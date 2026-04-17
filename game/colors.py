# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""Curses color pair constants and initialization."""

from __future__ import annotations

__version__ = "0.1.0"

# Color pair IDs — registered with curses.init_pair at startup.
CLR_EMPTY: int = 1
CLR_PLAYER: int = 2
CLR_WALLS: int = 3
CLR_CORRIDORS: int = 4
CLR_SPELLBOOKS: int = 5
CLR_DOORS: int = 6
CLR_MONSTER: int = 7

# Per-species colors.  Brown = COLOR_YELLOW without A_BOLD on dark
# backgrounds -- comfortable in a dark room (not too bright, not too dim).
CLR_BROWN: int = 8
CLR_FIRE: int = 9          # Bright red/yellow for burning tiles.
CLR_SCORCH: int = 10       # Dim residue after fire fades.
CLR_GRAY: int = 11         # Dull gray — rats, rubble.
CLR_FOOD: int = 12         # Green — edible items.


def init_colors() -> None:
    """Register the game's color pairs.  Must be called after initscr."""
    import curses
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(CLR_EMPTY, curses.COLOR_WHITE, -1)
    curses.init_pair(CLR_PLAYER, curses.COLOR_CYAN, -1)
    curses.init_pair(CLR_SPELLBOOKS, curses.COLOR_RED, -1)
    curses.init_pair(CLR_DOORS, curses.COLOR_YELLOW, -1)
    curses.init_pair(CLR_MONSTER, curses.COLOR_GREEN, -1)
    curses.init_pair(CLR_BROWN, curses.COLOR_YELLOW, -1)
    curses.init_pair(CLR_FIRE, curses.COLOR_RED, -1)
    curses.init_pair(CLR_SCORCH, curses.COLOR_YELLOW, -1)
    curses.init_pair(CLR_GRAY, curses.COLOR_WHITE, -1)
    curses.init_pair(CLR_FOOD, curses.COLOR_GREEN, -1)
