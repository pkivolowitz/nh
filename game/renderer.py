# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""Curses renderer: maps game-engine state to terminal output.

This is the *only* module that imports curses.  Everything else in
``game/`` is display-agnostic and can run headless.
"""

from __future__ import annotations

__version__ = "0.1.0"

import curses
import time
from typing import Optional

from game.constants import (
    BOARD_COLUMNS,
    BOARD_ROWS,
    BOARD_TOP_OFFSET,
    BOARD_IDENTITY_ROW,
    BOARD_MESSAGE_ROW,
    MIN_TERMINAL_COLS,
    SIDEBAR_GAP,
    MAX_INVENTORY_SLOTS,
    CH_HLINE, CH_VLINE,
    CH_ULCORNER, CH_URCORNER, CH_LLCORNER, CH_LRCORNER,
    CH_TTEE, CH_BTEE, CH_LTEE, CH_RTEE,
    CH_PLUS, CH_BULLET,
    DOWN_STAIRS, UP_STAIRS, DOOR_CLOSED_SYM,
    DEFAULT_TORCH_RADIUS,
)
from game.cell import CellBaseType, DoorState
from game.coordinate import Coordinate
from game.board import Board
from game.player import Player, Trait
from game.items import index_to_letter
from game.colors import (
    CLR_EMPTY, CLR_PLAYER, CLR_SPELLBOOKS, CLR_MONSTER,
    CLR_FIRE, CLR_SCORCH,
    init_colors,
)
from game.effects import EffectType

# Map engine display constants → curses ACS characters.
# Populated once after initscr via ``_build_acs_map``.
_acs_map: dict[int, int] = {}


def _build_acs_map() -> None:
    """Populate the engine-constant → ACS-character mapping.

    Must be called after ``curses.initscr()``.
    """
    _acs_map.clear()
    _acs_map[CH_HLINE] = curses.ACS_HLINE
    _acs_map[CH_VLINE] = curses.ACS_VLINE
    _acs_map[CH_ULCORNER] = curses.ACS_ULCORNER
    _acs_map[CH_URCORNER] = curses.ACS_URCORNER
    _acs_map[CH_LLCORNER] = curses.ACS_LLCORNER
    _acs_map[CH_LRCORNER] = curses.ACS_LRCORNER
    _acs_map[CH_TTEE] = curses.ACS_TTEE
    _acs_map[CH_BTEE] = curses.ACS_BTEE
    _acs_map[CH_LTEE] = curses.ACS_LTEE
    _acs_map[CH_RTEE] = curses.ACS_RTEE
    _acs_map[CH_PLUS] = curses.ACS_PLUS
    _acs_map[CH_BULLET] = curses.ACS_BULLET


def _resolve_ch(ch: int) -> int:
    """Convert an engine display constant to a curses-renderable value."""
    return _acs_map.get(ch, ch)


class Renderer:
    """Draws the game state using curses windows.

    Owns the map window and sidebar window.  Call ``draw`` after each
    engine step to update the display.
    """

    def __init__(self) -> None:
        self.map_win: Optional[curses.window] = None
        self.sidebar_win: Optional[curses.window] = None
        self.status_win: Optional[curses.window] = None
        self.status_cols: int = 0
        self.sidebar_rows: int = 0
        self.sidebar_cols: int = 0
        self.show_original: bool = False
        self.detail_mode: bool = False
        # Per-frame set of (row, col) tuples the player can currently see.
        self._visible_cells: set[tuple[int, int]] = set()
        # Last-seen monster positions: (row, col) → (symbol, color_pair).
        # Cleared on level change; entries removed when player re-sees
        # the cell and the monster is gone.
        self._remembered_monsters: dict[tuple[int, int], tuple[int, int]] = {}
        # Remembered objects (items, stairs): (row, col) → (ch, attr).
        # Persists once seen; updated with reality when cell is visible
        # again (e.g. monster picked up a potion → memory cleared).
        self._remembered_features: dict[tuple[int, int], tuple[int, int]] = {}
        # Track level so we can clear memories on level change.
        self._last_level: int = -1

    # ------------------------------------------------------------------
    # Setup / teardown
    # ------------------------------------------------------------------

    def init(self, stdscr: curses.window) -> None:
        """Create windows and initialize curses subsystems.

        Called once from the main curses wrapper.
        """
        init_colors()
        _build_acs_map()
        curses.curs_set(0)

        term_rows, term_cols = stdscr.getmaxyx()
        if term_cols < MIN_TERMINAL_COLS:
            raise RuntimeError(
                f"Terminal must be at least {MIN_TERMINAL_COLS} columns "
                f"wide (currently {term_cols})."
            )

        map_rows = BOARD_TOP_OFFSET + BOARD_ROWS
        map_cols = BOARD_COLUMNS
        self.map_win = curses.newwin(map_rows, map_cols, 0, 0)
        self.map_win.keypad(True)
        self.map_win.timeout(50)

        # Status window spans the full terminal width below the map.
        status_top = map_rows
        self.status_cols = term_cols
        self.status_win = curses.newwin(
            2, self.status_cols, status_top, 0,
        )

        self.sidebar_cols = term_cols - map_cols - SIDEBAR_GAP
        self.sidebar_rows = map_rows
        self.sidebar_win = curses.newwin(
            self.sidebar_rows, self.sidebar_cols,
            0, map_cols + SIDEBAR_GAP,
        )

    # ------------------------------------------------------------------
    # Full-frame draw
    # ------------------------------------------------------------------

    def draw(self, board: Board, player: Player,
             current_level: int, turn: int) -> None:
        """Render the complete frame: identity, map, monsters, player, status."""
        assert self.map_win is not None and self.sidebar_win is not None and self.status_win is not None
        # Clear memories when the player changes level.
        if current_level != self._last_level:
            self._remembered_monsters.clear()
            self._remembered_features.clear()
            self._last_level = current_level
        self._draw_board(board, player)
        self._draw_effects(board)
        self._draw_monsters(board, player)
        self._draw_player(player)
        # Identity goes after _draw_board (which calls erase()) so it
        # isn't wiped along with the previous frame.
        self._draw_identity(player)
        self._draw_time()
        self.map_win.noutrefresh()
        self._draw_status(board, player, current_level, turn)
        self.status_win.noutrefresh()
        self._draw_sidebar(player, current_level)
        self.sidebar_win.noutrefresh()
        curses.doupdate()

    # ------------------------------------------------------------------
    # Identity line (row 0) — name, role, race, alignment
    # ------------------------------------------------------------------

    def _draw_identity(self, player: Player) -> None:
        """Render the player identity line at the top of the map window.

        Format: "{name} the {role}, {race} {alignment}".  The clock is
        drawn separately at the right edge of the same row.
        """
        win = self.map_win
        if win is None:
            return
        win.move(BOARD_IDENTITY_ROW, 0)
        win.clrtoeol()

        identity: str = player.name
        # Leave room on the right for the clock (9 chars: " HH:MM:SS").
        identity = identity[:BOARD_COLUMNS - 10]

        attr = curses.color_pair(CLR_PLAYER) | curses.A_BOLD
        win.attron(attr)
        try:
            win.addstr(BOARD_IDENTITY_ROW, 0, identity)
        except curses.error:
            pass
        win.attroff(attr)

    # ------------------------------------------------------------------
    # Message line (row 1)
    # ------------------------------------------------------------------

    def show_message(self, msg: str) -> None:
        """Display a message on the message line just above the map.

        If the message is too long for one line, it is split at word
        boundaries and displayed in pages separated by "--More--"
        prompts.  The player presses any key to advance.
        """
        if self.map_win is None or not msg:
            return
        max_w: int = BOARD_COLUMNS - 1
        more_tag: str = " --More--"
        usable: int = max_w - len(more_tag)

        # Fast path: fits on one line.
        if len(msg) <= max_w:
            self.map_win.move(BOARD_MESSAGE_ROW, 0)
            self.map_win.clrtoeol()
            try:
                self.map_win.addstr(BOARD_MESSAGE_ROW, 0, msg)
            except curses.error:
                pass
            return

        # Split into chunks that fit with room for "--More--".
        chunks: list[str] = []
        remaining: str = msg
        while remaining:
            if len(remaining) <= max_w:
                chunks.append(remaining)
                break
            # Find the last space within the usable width.
            split_at: int = remaining.rfind(" ", 0, usable + 1)
            if split_at <= 0:
                split_at = usable  # No space — hard break.
            chunks.append(remaining[:split_at])
            remaining = remaining[split_at:].lstrip()

        for i, chunk in enumerate(chunks):
            self.map_win.move(BOARD_MESSAGE_ROW, 0)
            self.map_win.clrtoeol()
            is_last: bool = i == len(chunks) - 1
            if is_last:
                display: str = chunk[:max_w]
            else:
                display = chunk + more_tag
            try:
                self.map_win.addstr(BOARD_MESSAGE_ROW, 0, display)
            except curses.error:
                pass
            if not is_last:
                self.map_win.noutrefresh()
                curses.doupdate()
                self.map_win.timeout(-1)
                self.map_win.getch()
                self.map_win.timeout(50)

    def clear_info_line(self) -> None:
        """Erase the message line."""
        if self.map_win is None:
            return
        self.map_win.move(BOARD_MESSAGE_ROW, 0)
        self.map_win.clrtoeol()

    # ------------------------------------------------------------------
    # Board rendering
    # ------------------------------------------------------------------

    def _draw_board(self, board: Board, player: Player,
                    tr: float = DEFAULT_TORCH_RADIUS) -> None:
        """Render cells the player can currently see.

        Cells outside line of sight are not rendered at all — there is
        no persistent terrain memory.  Monster memory is handled
        separately in ``_draw_monsters``.
        """
        win = self.map_win
        assert win is not None
        win.erase()
        self._visible_cells.clear()

        # Pre-compute once per frame.
        pr: int = player.pos.r
        pc: int = player.pos.c
        tr_sq: float = tr * tr
        in_corridor: bool = board.is_corridor(player.pos)
        cells = board.cells
        ppos = player.pos

        for r in range(BOARD_ROWS):
            row = cells[r]
            for c in range(BOARD_COLUMNS):
                cell = row[c]

                if cell.base_type == CellBaseType.EMPTY:
                    continue

                coord = Coordinate(r, c)

                if self.show_original:
                    self._show_cell(board, coord, cell, force_original=True)
                    continue

                # Walls, doors, and corridors persist once seen — structural.
                if (cell.base_type in (CellBaseType.WALL, CellBaseType.DOOR,
                                       CellBaseType.CORRIDOR)
                        and cell.is_known):
                    self._show_cell(board, coord, cell)
                    continue

                # Visibility check: within personal torch range or on
                # a cell illuminated by a dungeon torch.
                dr: int = r - pr
                dc: int = c - pc
                within_personal: bool = dr * dr + dc * dc < tr_sq
                if not (within_personal or cell.lit):
                    # Not visible — draw remembered feature if any.
                    feat = self._remembered_features.get((r, c))
                    if feat is not None:
                        win.attron(feat[1])
                        try:
                            win.addch(BOARD_TOP_OFFSET + r, c, feat[0])
                        except curses.error:
                            pass
                        win.attroff(feat[1])
                    continue

                # Corridor walls: don't reveal until first seen.
                if (in_corridor
                        and cell.base_type == CellBaseType.WALL
                        and not cell.is_known):
                    continue

                if not board.line_of_sight(ppos, coord):
                    # No LOS — draw remembered feature if any.
                    feat = self._remembered_features.get((r, c))
                    if feat is not None:
                        win.attron(feat[1])
                        try:
                            win.addch(BOARD_TOP_OFFSET + r, c, feat[0])
                        except curses.error:
                            pass
                        win.attroff(feat[1])
                    continue

                # Currently visible — mark known and draw.
                cell.is_known = True
                self._visible_cells.add((r, c))
                self._show_cell(board, coord, cell)

                # Remember interesting features (items, stairs).
                # Plain floor and corridors are not remembered.
                key = (r, c)
                item_sym = board.get_symbol(coord)
                if item_sym >= 0:
                    # Item on floor — remember it.
                    ch = _resolve_ch(item_sym)
                    attr = self._cell_attr(ch, item_sym, CellBaseType.ROOM)
                    self._remembered_features[key] = (ch, attr)
                elif cell.display_c in (DOWN_STAIRS, UP_STAIRS):
                    ch = _resolve_ch(cell.display_c)
                    attr = self._cell_attr(ch, cell.display_c, cell.base_type)
                    self._remembered_features[key] = (ch, attr)
                else:
                    # Cell is plain floor or corridor — forget it.
                    self._remembered_features.pop(key, None)

    def _show_cell(self, board: Board, coord: Coordinate, cell,
                   force_original: bool = False) -> None:
        """Render a single cell with appropriate attributes."""
        win = self.map_win
        assert win is not None

        if force_original:
            ch = _resolve_ch(cell.original_c)
            win.addch(BOARD_TOP_OFFSET + coord.r, coord.c, ch)
            return

        # Item on floor overrides cell display.
        sym = board.get_symbol(coord)
        if sym >= 0:
            render_type = CellBaseType.ROOM
        else:
            sym = cell.display_c
            render_type = cell.base_type

        ch = _resolve_ch(sym)
        attr = self._cell_attr(ch, sym, render_type)
        win.attron(attr)
        try:
            win.addch(BOARD_TOP_OFFSET + coord.r, coord.c, ch)
        except curses.error:
            pass  # Writing to bottom-right corner of window can raise.
        win.attroff(attr)

    @staticmethod
    def _cell_attr(ch: int, sym: int, cell_type: CellBaseType) -> int:
        """Choose curses attributes for a rendered symbol."""
        if cell_type == CellBaseType.DOOR:
            return curses.A_NORMAL
        if ch == curses.ACS_BULLET:
            return curses.A_DIM
        if sym == ord("+"):
            return curses.color_pair(CLR_SPELLBOOKS)
        if sym == ord("#"):
            return curses.A_DIM
        if sym in (ord("<"), ord(">")):
            return curses.A_BOLD
        return curses.A_NORMAL

    # ------------------------------------------------------------------
    # Ephemeral effects (fire, scorch marks, etc.)
    # ------------------------------------------------------------------

    def _draw_effects(self, board: Board) -> None:
        """Render active tile effects over the board.

        Fire flickers between symbols in bright red.  Scorch marks
        are dim yellow residue.  Effects only render on cells the
        player can currently see.
        """
        win = self.map_win
        assert win is not None

        for pos, effect in board.effects.items():
            if (pos.r, pos.c) not in self._visible_cells:
                continue

            sym: int = effect.symbol
            if effect.effect_type == EffectType.FIRE:
                attr = curses.color_pair(CLR_FIRE) | curses.A_BOLD
            elif effect.effect_type == EffectType.SCORCH:
                attr = curses.color_pair(CLR_SCORCH) | curses.A_DIM
            else:
                attr = curses.A_NORMAL

            win.attron(attr)
            try:
                win.addch(BOARD_TOP_OFFSET + pos.r, pos.c, sym)
            except curses.error:
                pass
            win.attroff(attr)

    # ------------------------------------------------------------------
    # Monsters
    # ------------------------------------------------------------------

    def _draw_monsters(self, board: Board, player: Player,
                       tr: float = DEFAULT_TORCH_RADIUS) -> None:
        """Draw monsters visible to the player, plus remembered ones.

        A monster is visible when the player has line of sight and
        either the monster is within the player's personal torch
        radius or the monster's cell is illuminated by a dungeon torch.

        When a monster is seen, its position is remembered.  If the
        player loses sight of that cell, the monster is drawn at its
        last-known position until the player can see that cell again.
        """
        win = self.map_win
        assert win is not None
        visible = self._visible_cells

        # Clear remembered monsters from cells the player can now see
        # (reality replaces memory).
        for rc in list(self._remembered_monsters):
            if rc in visible:
                del self._remembered_monsters[rc]

        # Draw live monsters and update memory.
        for monster in board.get_all_monsters():
            coord = monster.pos
            key = (coord.r, coord.c)

            if self.show_original or key in visible:
                # Currently visible — draw live and remember.
                self._remembered_monsters[key] = (
                    monster.symbol, monster.color_pair
                )
                attr = curses.color_pair(monster.color_pair)
                win.attron(attr)
                try:
                    win.addch(
                        BOARD_TOP_OFFSET + coord.r, coord.c, monster.symbol
                    )
                except curses.error:
                    pass
                win.attroff(attr)

        # Draw remembered monsters in cells no longer visible.
        for (mr, mc), (sym, cpair) in self._remembered_monsters.items():
            if (mr, mc) in visible:
                continue  # Already drawn live above.
            attr = curses.color_pair(cpair) | curses.A_DIM
            win.attron(attr)
            try:
                win.addch(BOARD_TOP_OFFSET + mr, mc, sym)
            except curses.error:
                pass
            win.attroff(attr)

    # ------------------------------------------------------------------
    # Player
    # ------------------------------------------------------------------

    def _draw_player(self, player: Player) -> None:
        """Draw the player '@' glyph."""
        win = self.map_win
        assert win is not None
        attr = curses.color_pair(CLR_PLAYER) | curses.A_BOLD
        win.attron(attr)
        win.addch(BOARD_TOP_OFFSET + player.pos.r, player.pos.c, ord("@"))
        win.attroff(attr)

    # ------------------------------------------------------------------
    # Status lines
    # ------------------------------------------------------------------

    @staticmethod
    def _fmt_stat_col(label: str, cur: int, mx: int,
                      label_w: int, num_w: int) -> str:
        """Format ``LABEL:CUR/MAX`` with strict fixed-width fields.

        ``label`` is right-aligned within ``label_w`` chars and the
        numeric values are right-aligned within ``num_w`` chars each.
        Two columns built with the same widths line up exactly.
        """
        return f"{label:>{label_w}}:{cur:>{num_w}d}/{mx:>{num_w}d}"

    def _draw_status(self, board: Board, player: Player,
                     current_level: int, turn: int) -> None:
        """Render the two status rows in the full-width status window.

        Row 1 (volatile / game state):
            HLTH  CNC  LVL  EXP  Dlvl  Turn
        Row 2 (attributes / inventory):
            STR  INT  CON  DEX  Items  Wt/Max
        """
        win = self.status_win
        assert win is not None
        win.erase()
        attr = curses.color_pair(CLR_EMPTY)

        cur = player.current_traits
        mx = player.maximum_traits
        fmt = self._fmt_stat_col

        # Row 1: health, concentration, level, exp, dungeon level, turn.
        r1_parts: list[str] = [
            fmt("HLTH", cur[Trait.HEALTH], mx[Trait.HEALTH], 4, 3),
            fmt("CNC", cur[Trait.CONCENTRATION], mx[Trait.CONCENTRATION], 4, 3),
            fmt("LVL", cur[Trait.LEVEL], mx[Trait.LEVEL], 4, 3),
            f"{'EXP':>4}:{cur[Trait.EXPERIENCE]:>6d}",
            f"Dlvl:{current_level:>4d}",
            f"Turn:{turn:>6d}",
        ]

        # Row 2: str, int, con, dex, items, weight/max.
        carry_wt: int = player.weight_of_inventory()
        max_wt: int = player.max_carry_weight()
        r2_parts: list[str] = [
            fmt("STR", cur[Trait.STRENGTH], mx[Trait.STRENGTH], 4, 3),
            fmt("INT", cur[Trait.INTELLIGENCE], mx[Trait.INTELLIGENCE], 4, 3),
            fmt("CON", cur[Trait.CONSTITUTION], mx[Trait.CONSTITUTION], 4, 3),
            fmt("DEX", cur[Trait.DEXTERITY], mx[Trait.DEXTERITY], 4, 3),
            f"Items:{player.inventory_count():>2d}/{MAX_INVENTORY_SLOTS:>2d}",
            f"Wt:{carry_wt:>4d}/{max_wt:>4d}",
        ]

        sep: str = "  "
        row_top: str = sep.join(r1_parts)
        row_bot: str = sep.join(r2_parts)

        win.attron(attr)
        try:
            win.addstr(0, 0, row_top)
            win.addstr(1, 0, row_bot)
        except curses.error:
            pass
        win.attroff(attr)

    def _draw_time(self) -> None:
        """Draw the wall-clock time at the right edge of the identity row."""
        win = self.map_win
        if win is None:
            return
        ts = time.strftime("%H:%M:%S")
        try:
            win.addstr(BOARD_IDENTITY_ROW, BOARD_COLUMNS - 8, ts)
        except curses.error:
            pass

    def update_clock(self) -> None:
        """Lightweight clock refresh — no full redraw.

        Called from the input poll loop so the clock ticks while
        waiting for player input without erasing the message line.
        """
        self._draw_time()
        if self.map_win is not None:
            self.map_win.noutrefresh()
            curses.doupdate()

    # ------------------------------------------------------------------
    # Sidebar
    # ------------------------------------------------------------------

    def _draw_sidebar(self, player: Player, current_level: int) -> None:
        """Render the inventory list in the sidebar.

        Wt, Items, and Dlvl now appear in the bottom status rows of
        the main map, so the sidebar is just the inventory listing.
        """
        win = self.sidebar_win
        assert win is not None
        win.erase()

        # Header.
        attr = curses.A_BOLD
        if self.detail_mode:
            win.addstr(0, 1, "Inventory [detail]", attr)
        else:
            win.addstr(0, 1, "Inventory", attr)

        row = 2
        max_rows = self.sidebar_rows
        max_cols = self.sidebar_cols
        for i in range(len(player.inventory)):
            if row >= max_rows - 1:
                break
            item = player.inventory[i]
            if item is None:
                continue

            letter = index_to_letter(i)
            line = f"{letter} - {item.item_name}"
            if len(line) > max_cols - 2:
                line = line[: max_cols - 2]

            item_attr = curses.A_NORMAL
            if item.symbol == ord("+"):
                item_attr = curses.color_pair(CLR_SPELLBOOKS)

            win.attron(item_attr)
            win.addstr(row, 1, line)
            win.attroff(item_attr)
            row += 1

            if self.detail_mode and row < max_rows - 1:
                detail = f"    Wt:{item.weight()}"
                names = {1: "Potion", 2: "Scroll", 3: "Spellbook"}
                extra = names.get(int(item.type), "")
                if extra:
                    detail += f"  {extra}"
                if len(detail) > max_cols - 2:
                    detail = detail[: max_cols - 2]
                win.addstr(row, 1, detail)
                row += 1

    # ------------------------------------------------------------------
    # Help overlay (layered, displayed in the sidebar)
    # ------------------------------------------------------------------

    # Each help page is a (title, lines) tuple.  Pages are navigated
    # by number keys; ESC or 'q' dismisses.
    _HELP_PAGES: list[tuple[str, list[str]]] = [
        ("Help — Overview", [
            "Movement: hjklyubn (vi keys)",
            "  SHIFT = run until blocked",
            "  1-9 prefix = repeat N steps",
            "",
            "Actions:",
            "  , = pick up item",
            "  d = drop item",
            "  e = eat food (restores HP)",
            "  T = throw rock (+ direction)",
            "  o = open door (+ direction)",
            "  c = close door (+ direction)",
            "  ^K = kick (+ direction)",
            "  . = rest one turn",
            "  > = descend stairs",
            "  < = ascend stairs",
            "",
            "Magic:",
            "  r = read spellbook",
            "  z = cast spell",
            "",
            "Other:",
            "  i = toggle inventory detail",
            "  t = toggle debug view",
            "  q = save and quit",
            "  ? = this help",
            "",
            "[1-3] More pages  [q/ESC] Close",
        ]),
        ("Help — Magic", [
            "Magic is learned, not memorized.",
            "",
            "Read a spellbook (r) to learn a",
            "school or gain proficiency.",
            "Books crumble to dust once read.",
            "",
            "Cast with z, then pick school:",
            "  f=Fire  w=Water  a=Air",
            "  e=Earth h=Healing",
            "  t=Teleport r=Force",
            "Then pick a direction.",
            "",
            "Proficiency tiers:",
            "  Novice     - wild, dangerous",
            "  Apprentice - some control",
            "  Journeyman - reliable",
            "  Expert     - precise",
            "  Master     - surgical",
            "",
            "Higher tiers cost less Conc",
            "and produce cleaner results.",
            "",
            "Concentration regenerates over",
            "time (faster with high INT).",
            "",
            "[1-3] More pages  [q/ESC] Close",
        ]),
        ("Help — Combat & Survival", [
            "Bump into a monster to attack.",
            "Monsters bump-attack you too.",
            "",
            "HP regenerates slowly when no",
            "monster is adjacent. CON governs",
            "how quickly you heal.",
            "",
            "Concentration regenerates over",
            "time. INT governs the rate.",
            "",
            "Kicking at nothing risks",
            "straining your leg (1-2 dmg).",
            "",
            "Noise matters:",
            "  Walking is quiet, running loud",
            "  Doors creak when opened",
            "  Kicking reverberates",
            "  Casting fire roars",
            "",
            "Monsters hear noise and",
            "investigate. Plan accordingly.",
            "",
            "The game saves when you quit.",
            "Death deletes the save.",
            "",
            "[1-3] More pages  [q/ESC] Close",
        ]),
    ]

    def show_help(self) -> None:
        """Display the layered help system in the sidebar.

        Takes over the sidebar until dismissed.  Number keys
        switch pages; ESC or q returns to normal display.
        """
        win = self.sidebar_win
        if win is None:
            return

        page: int = 0

        while True:
            win.erase()
            title, lines = self._HELP_PAGES[page]

            # Title.
            try:
                win.addstr(0, 1, title, curses.A_BOLD)
            except curses.error:
                pass

            # Body.
            for i, line in enumerate(lines):
                row: int = i + 2
                if row >= self.sidebar_rows - 1:
                    break
                try:
                    text: str = line[:self.sidebar_cols - 2]
                    win.addstr(row, 1, text)
                except curses.error:
                    pass

            win.noutrefresh()
            curses.doupdate()

            # Wait for input.
            assert self.map_win is not None
            self.map_win.timeout(-1)
            ch: int = self.map_win.getch()
            self.map_win.timeout(50)

            # Page selection by number.
            if ch in (ord("1"), ord("2"), ord("3")):
                idx: int = ch - ord("1")
                if 0 <= idx < len(self._HELP_PAGES):
                    page = idx
                    continue

            # Dismiss.
            if ch in (27, ord("q"), ord("?")):
                break

    # ------------------------------------------------------------------
    # Input helpers
    # ------------------------------------------------------------------

    def getch(self) -> int:
        """Non-blocking read from the map window (50 ms timeout)."""
        assert self.map_win is not None
        return self.map_win.getch()

    def getch_blocking(self) -> int:
        """Blocking read from the map window."""
        assert self.map_win is not None
        self.map_win.timeout(-1)
        ch = self.map_win.getch()
        self.map_win.timeout(50)
        return ch

    # ------------------------------------------------------------------
    # Cursor targeting
    # ------------------------------------------------------------------

    # vi-key → (dr, dc) for cursor movement.
    _CURSOR_KEYS: dict[int, tuple[int, int]] = {
        ord("k"): (-1, 0), ord("j"): (1, 0),
        ord("l"): (0, 1),  ord("h"): (0, -1),
        ord("u"): (-1, 1), ord("y"): (-1, -1),
        ord("n"): (1, 1),  ord("b"): (1, -1),
        curses.KEY_UP: (-1, 0), curses.KEY_DOWN: (1, 0),
        curses.KEY_RIGHT: (0, 1), curses.KEY_LEFT: (0, -1),
    }

    def select_target(self, board: Board,
                      player_pos: Coordinate) -> Optional[Coordinate]:
        """Let the player move a cursor to choose a target cell.

        The cursor starts at the player's position.  Movement keys
        advance one cell at a time.  The cursor can move freely
        anywhere on the board — no LOS restriction, so it doesn't
        reveal wall positions in the dark.  The spell itself handles
        wall collision at cast time.

        Confirm with '.' or Enter.  Cancel with Escape.

        Returns the selected Coordinate, or None if cancelled.
        """
        win = self.map_win
        assert win is not None

        cr: int = player_pos.r
        cc: int = player_pos.c
        old_timeout = 50
        win.timeout(-1)  # Blocking while targeting.

        try:
            while True:
                # Draw cursor — bright reverse-video 'X'.
                screen_r: int = BOARD_TOP_OFFSET + cr
                attr = curses.A_REVERSE | curses.A_BOLD
                win.attron(attr)
                try:
                    win.addch(screen_r, cc, ord("X"))
                except curses.error:
                    pass
                win.attroff(attr)
                win.noutrefresh()
                curses.doupdate()

                ch: int = win.getch()

                if ch == 27:  # Escape — cancel.
                    return None

                if ch in (ord("."), ord("\n"), ord("\r")):
                    return Coordinate(cr, cc)

                move = self._CURSOR_KEYS.get(ch)
                if move is None:
                    continue

                nr: int = cr + move[0]
                nc: int = cc + move[1]

                # Stay in bounds.
                if not (0 <= nr < BOARD_ROWS and 0 <= nc < BOARD_COLUMNS):
                    continue

                # Erase old cursor position by restoring what was there.
                self._restore_cell(board, cr, cc, player_pos)

                cr, cc = nr, nc
        finally:
            win.timeout(old_timeout)
            # Restore the cell under the final cursor position.
            self._restore_cell(board, cr, cc, player_pos)

    def _restore_cell(self, board: Board, r: int, c: int,
                      player_pos: Coordinate) -> None:
        """Redraw a single cell to erase a targeting cursor overlay."""
        win = self.map_win
        assert win is not None
        screen_r: int = BOARD_TOP_OFFSET + r

        if r == player_pos.r and c == player_pos.c:
            attr = curses.color_pair(CLR_PLAYER) | curses.A_BOLD
            win.attron(attr)
            try:
                win.addch(screen_r, c, ord("@"))
            except curses.error:
                pass
            win.attroff(attr)
            return

        # Check for a monster.
        coord = Coordinate(r, c)
        monster = board.get_monster_at(coord)
        if monster is not None and (r, c) in self._visible_cells:
            attr = curses.color_pair(monster.color_pair)
            win.attron(attr)
            try:
                win.addch(screen_r, c, monster.symbol)
            except curses.error:
                pass
            win.attroff(attr)
            return

        # Fall back to the cell display.
        cell = board.cells[r][c]
        self._show_cell(board, coord, cell)
