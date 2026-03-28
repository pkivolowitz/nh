# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""Board dimensions, display character constants, and game parameters.

Display constants (CH_*) are curses-independent integers used by the
game engine.  The renderer maps them to actual curses ACS characters
at draw time so the engine can run headless for ML training.
"""

__version__ = "0.1.0"

# ---------------------------------------------------------------------------
# Board geometry
# ---------------------------------------------------------------------------
BOARD_COLUMNS: int = 80
BOARD_ROWS: int = 21
BOARD_TOP_OFFSET: int = 1
BOARD_STATUS_OFFSET: int = BOARD_ROWS + BOARD_TOP_OFFSET

# ---------------------------------------------------------------------------
# Room generation limits
# ---------------------------------------------------------------------------
MIN_ROOMS: int = 6
MAX_ROOMS: int = 9
MIN_ROOM_WIDTH: int = 3
MAX_ROOM_WIDTH: int = 9
MIN_ROOM_HEIGHT: int = 4
MAX_ROOM_HEIGHT: int = 8

# ---------------------------------------------------------------------------
# Display character constants — curses-independent.
# Values are chosen well above the ASCII range so they never collide
# with ordinary characters.
# ---------------------------------------------------------------------------
CH_HLINE: int = 1001
CH_VLINE: int = 1002
CH_ULCORNER: int = 1003
CH_URCORNER: int = 1004
CH_LLCORNER: int = 1005
CH_LRCORNER: int = 1006
CH_TTEE: int = 1007
CH_BTEE: int = 1008
CH_LTEE: int = 1009
CH_RTEE: int = 1010
CH_PLUS: int = 1011
CH_BULLET: int = 1012

# ---------------------------------------------------------------------------
# Stair and door symbols (ASCII range — used by game logic)
# ---------------------------------------------------------------------------
DOWN_STAIRS: int = ord(">")
UP_STAIRS: int = ord("<")
DOOR_CLOSED_SYM: int = ord("+")

# ---------------------------------------------------------------------------
# Torch / visibility
# ---------------------------------------------------------------------------
DEFAULT_TORCH_RADIUS: float = 2.5

# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------
MAX_INVENTORY_SLOTS: int = 52

# ---------------------------------------------------------------------------
# Terminal layout
# ---------------------------------------------------------------------------
MIN_TERMINAL_COLS: int = 120
SIDEBAR_GAP: int = 1
