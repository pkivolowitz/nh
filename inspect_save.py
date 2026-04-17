#!/usr/bin/env python3
"""Load a PNH save file and dump a readable text snapshot.

Usage: python inspect_save.py [path]
Default path: ~/.pnh/savegame.pkl
"""

import os
import sys
import pickle

# Ensure the project root is on the path so game/ imports work.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game.drawing_support import initialize_corner_map
from game.brain import BrainRegistry
from game.constants import (
    BOARD_ROWS, BOARD_COLUMNS,
    CH_HLINE, CH_VLINE,
    CH_ULCORNER, CH_URCORNER, CH_LLCORNER, CH_LRCORNER,
    CH_TTEE, CH_BTEE, CH_LTEE, CH_RTEE,
    CH_PLUS, CH_BULLET,
)
from game.cell import CellBaseType, DoorState
from game.player import Trait
from game.items import index_to_letter

# Map engine display constants to Unicode box-drawing characters
# so the dump is readable without curses.
_UNICODE_MAP: dict[int, str] = {
    CH_HLINE:    "\u2500",   # ─
    CH_VLINE:    "\u2502",   # │
    CH_ULCORNER: "\u250C",   # ┌
    CH_URCORNER: "\u2510",   # ┐
    CH_LLCORNER: "\u2514",   # └
    CH_LRCORNER: "\u2518",   # ┘
    CH_TTEE:     "\u252C",   # ┬
    CH_BTEE:     "\u2534",   # ┴
    CH_LTEE:     "\u251C",   # ├
    CH_RTEE:     "\u2524",   # ┤
    CH_PLUS:     "\u253C",   # ┼
    CH_BULLET:   "\u00B7",   # ·
}


def _ch(sym: int) -> str:
    """Convert an engine display constant to a printable character."""
    if sym in _UNICODE_MAP:
        return _UNICODE_MAP[sym]
    if 32 <= sym < 127:
        return chr(sym)
    return " "


def dump(engine, out=sys.stdout) -> None:
    """Print a full text snapshot of the game state."""
    board = engine.boards[engine.current_board_index]
    player = engine.player
    level = engine.current_board_index + 1

    # -- header --
    out.write(f"=== PNH Snapshot ===\n")
    out.write(f"Level: {level}  Turn: {engine.turn_counter}\n")
    out.write(f"Player: {player.name} ({player.role} {player.race} {player.alignment})\n")
    out.write(f"Position: ({player.pos.r}, {player.pos.c})\n")
    traits = {t.name: player.current_traits[t] for t in Trait if t != Trait.TRAIT_COUNT}
    max_traits = {t.name: player.maximum_traits[t] for t in Trait if t != Trait.TRAIT_COUNT}
    out.write("Traits: " + ", ".join(
        f"{k}={v}/{max_traits[k]}" for k, v in traits.items()
    ) + "\n")
    out.write("\n")

    # -- build the map grid --
    # Start with cell display characters.
    grid: list[list[str]] = []
    for r in range(BOARD_ROWS):
        row: list[str] = []
        for c in range(BOARD_COLUMNS):
            cell = board.cells[r][c]
            if cell.base_type == CellBaseType.EMPTY:
                row.append(" ")
            else:
                # Items on floor override cell display.
                coord_key = None
                for coord, items in board.goodies.items():
                    if coord.r == r and coord.c == c and items:
                        coord_key = items[-1].symbol
                        break
                if coord_key is not None:
                    row.append(_ch(coord_key))
                else:
                    row.append(_ch(cell.display_c))
        grid.append(row)

    # Overlay monsters.
    for monster in board.get_all_monsters():
        mr, mc = monster.pos.r, monster.pos.c
        grid[mr][mc] = chr(monster.symbol)

    # Overlay effects.
    if hasattr(board, "effects"):
        for pos, effect in board.effects.items():
            grid[pos.r][pos.c] = chr(effect.symbol)

    # Overlay player.
    grid[player.pos.r][player.pos.c] = "@"

    # -- print map with row numbers --
    out.write("     " + "".join(f"{c % 10}" for c in range(BOARD_COLUMNS)) + "\n")
    out.write("     " + "".join(
        f"{c // 10}" if c % 10 == 0 else " " for c in range(BOARD_COLUMNS)
    ) + "\n")
    for r, row in enumerate(grid):
        out.write(f"{r:3d}  " + "".join(row) + "\n")
    out.write("\n")

    # -- monsters --
    monsters = list(board.get_all_monsters())
    if monsters:
        out.write("Monsters:\n")
        for m in monsters:
            out.write(f"  {chr(m.symbol)} '{m.name}' at ({m.pos.r},{m.pos.c})"
                      f"  HP={m.hp}/{m.max_hp}\n")
        out.write("\n")

    # -- items on floor --
    if board.goodies:
        out.write("Items on floor:\n")
        for coord, items in board.goodies.items():
            for it in items:
                out.write(f"  ({coord.r},{coord.c}) {it.item_name}\n")
        out.write("\n")

    # -- inventory --
    inv_items = [(i, it) for i, it in enumerate(player.inventory) if it is not None]
    if inv_items:
        out.write("Inventory:\n")
        for i, it in inv_items:
            out.write(f"  {index_to_letter(i)}) {it.item_name}"
                      f" (x{it.number_of_like_items}, wt {it.weight()})\n")
        out.write("\n")

    # -- magic --
    if hasattr(player, "magic") and player.magic.schools:
        out.write("Magic:\n")
        for school, state in player.magic.schools.items():
            out.write(f"  {school.name}: XP={state.xp} tier={state.tier.name}\n")
        out.write("\n")

    # -- stairs --
    out.write(f"Upstairs: ({board.upstairs.r},{board.upstairs.c})\n")
    out.write(f"Downstairs: ({board.downstairs.r},{board.downstairs.c})\n")

    # -- doors --
    doors = []
    for r in range(BOARD_ROWS):
        for c in range(BOARD_COLUMNS):
            cell = board.cells[r][c]
            if cell.base_type == CellBaseType.DOOR:
                doors.append((r, c, cell.door_state.name))
    if doors:
        out.write("\nDoors:\n")
        for r, c, state in doors:
            out.write(f"  ({r},{c}) {state}\n")


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/.pnh/savegame.pkl")
    if not os.path.exists(path):
        print(f"No save file at {path}", file=sys.stderr)
        sys.exit(1)

    # Initialize singletons before unpickling.
    initialize_corner_map()
    BrainRegistry.init()

    with open(path, "rb") as f:
        engine = pickle.load(f)

    dump(engine)


if __name__ == "__main__":
    main()
