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
    BOARD_STATUS_OFFSET,
    MIN_TERMINAL_COLS,
    SIDEBAR_GAP,
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
from game.player import Player
from game.items import index_to_letter
from game.colors import (
    CLR_EMPTY, CLR_PLAYER, CLR_SPELLBOOKS, CLR_MONSTER,
    init_colors,
)

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
        self.sidebar_rows: int = 0
        self.sidebar_cols: int = 0
        self.show_original: bool = False
        self.detail_mode: bool = False

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

        map_rows = BOARD_TOP_OFFSET + BOARD_ROWS + 2
        map_cols = BOARD_COLUMNS
        self.map_win = curses.newwin(map_rows, map_cols, 0, 0)
        self.map_win.keypad(True)
        self.map_win.timeout(50)

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
        """Render the complete frame: map, monsters, player, sidebar, status."""
        assert self.map_win is not None and self.sidebar_win is not None
        self._draw_board(board, player)
        self._draw_monsters(board, player)
        self._draw_player(player)
        self._draw_status(board, player, current_level)
        self._draw_time()
        self.map_win.noutrefresh()
        self._draw_sidebar(player, current_level)
        self.sidebar_win.noutrefresh()
        curses.doupdate()

    # ------------------------------------------------------------------
    # Info line (top of map window)
    # ------------------------------------------------------------------

    def show_message(self, msg: str) -> None:
        """Display a message on the info line at the top of the map."""
        if self.map_win is None or not msg:
            return
        self.map_win.move(0, 0)
        self.map_win.clrtoeol()
        self.map_win.addstr(0, 0, msg[:BOARD_COLUMNS - 9])
        self._draw_time()

    def clear_info_line(self) -> None:
        """Erase the info line and redraw the clock."""
        if self.map_win is None:
            return
        self.map_win.move(0, 0)
        self.map_win.clrtoeol()
        self._draw_time()

    # ------------------------------------------------------------------
    # Board rendering
    # ------------------------------------------------------------------

    def _draw_board(self, board: Board, player: Player,
                    tr: float = DEFAULT_TORCH_RADIUS) -> None:
        """Render visible cells with fog of war."""
        win = self.map_win
        assert win is not None
        win.erase()

        for r in range(BOARD_ROWS):
            for c in range(BOARD_COLUMNS):
                coord = Coordinate(r, c)
                cell = board.cells[r][c]

                if cell.base_type == CellBaseType.EMPTY:
                    continue

                if self.show_original:
                    self._show_cell(board, coord, cell, force_original=True)
                    continue

                # Limit corridor wall visibility.
                if (board.is_corridor(player.pos)
                        and cell.base_type == CellBaseType.WALL
                        and not cell.is_known):
                    continue

                # Always show known structural elements.
                if (cell.base_type in (CellBaseType.WALL,
                                       CellBaseType.CORRIDOR,
                                       CellBaseType.DOOR)
                        or board.is_a_stairway(coord)):
                    if cell.is_known:
                        self._show_cell(board, coord, cell)
                        continue

                # Known floor with items.
                if (cell.base_type == CellBaseType.ROOM
                        and cell.is_known
                        and board.get_symbol(coord) >= 0):
                    self._show_cell(board, coord, cell)
                    continue

                # Lit cells that are known always render (lit rooms
                # stay visible after the player has seen them).
                if cell.is_known and cell.lit:
                    self._show_cell(board, coord, cell)
                    continue

                # Beyond torch range.
                if coord.distance(player.pos) >= tr:
                    continue

                # No LOS.
                if not board.line_of_sight(player.pos, coord):
                    continue

                # Visible — mark known and draw.
                cell.is_known = True
                self._show_cell(board, coord, cell)

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
    # Monsters
    # ------------------------------------------------------------------

    def _draw_monsters(self, board: Board, player: Player,
                       tr: float = DEFAULT_TORCH_RADIUS) -> None:
        """Draw monsters visible to the player.

        A monster is visible when the player has line of sight and
        either the monster is within the player's personal torch
        radius or the monster's cell is illuminated by a dungeon torch.
        """
        win = self.map_win
        assert win is not None

        for monster in board.get_all_monsters():
            coord = monster.pos

            if not self.show_original:
                mcell = board.cells[coord.r][coord.c]
                within_personal: bool = coord.distance(player.pos) < tr
                if not (within_personal or mcell.lit):
                    continue
                if not board.line_of_sight(player.pos, coord):
                    continue

            attr = curses.color_pair(monster.color_pair)
            win.attron(attr)
            try:
                win.addch(
                    BOARD_TOP_OFFSET + coord.r, coord.c, monster.symbol
                )
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

    def _draw_status(self, board: Board, player: Player,
                     current_level: int) -> None:
        """Render the two status lines below the map."""
        win = self.map_win
        assert win is not None
        attr = curses.color_pair(CLR_EMPTY)
        win.attron(attr)
        win.addstr(BOARD_STATUS_OFFSET, 0, player.status_line_upper())
        win.addstr(BOARD_STATUS_OFFSET + 1, 0, player.status_line_lower())
        win.attroff(attr)

    def _draw_time(self) -> None:
        """Draw the wall-clock time in the upper-right corner."""
        win = self.map_win
        if win is None:
            return
        ts = time.strftime("%H:%M:%S")
        try:
            win.addstr(0, BOARD_COLUMNS - 8, ts)
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
        """Render inventory and dungeon level in the sidebar."""
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
            if row >= max_rows - 4:
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

            if self.detail_mode and row < max_rows - 4:
                detail = f"    Wt:{item.weight()}"
                names = {1: "Potion", 2: "Scroll", 3: "Spellbook"}
                extra = names.get(int(item.type), "")
                if extra:
                    detail += f"  {extra}"
                if len(detail) > max_cols - 2:
                    detail = detail[: max_cols - 2]
                win.addstr(row, 1, detail)
                row += 1

        # Summary block.
        win.addstr(max_rows - 3, 1, f"Wt:{player.weight_of_inventory()}")
        win.addstr(max_rows - 2, 1,
                   f"Items:{player.inventory_count()}/{len(player.inventory)}")
        win.addstr(max_rows - 1, 1, f"Dlvl:{current_level}")

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
