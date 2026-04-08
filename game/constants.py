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
# Speed / energy system — drives turn ordering for all creatures
# ---------------------------------------------------------------------------
ENERGY_THRESHOLD: int = 12   # Energy needed to act; same as NetHack base speed
PLAYER_SPEED: int = 12       # Player speed matches base monster speed

# ---------------------------------------------------------------------------
# Monster spawning
# ---------------------------------------------------------------------------
MONSTER_ROOM_CHANCE: int = 40  # Percent chance a non-player room gets monsters

# ---------------------------------------------------------------------------
# Torch lighting — wall-mounted torches illuminate an area.  Overlapping
# torches can light an entire room.  Rooms without torches stay dark.
# ---------------------------------------------------------------------------
TORCH_LIGHT_RADIUS: float = 3.5    # Cells illuminated around each wall torch
TORCH_ROOM_CHANCE: int = 70        # Percent chance a room gets any torches
MAX_TORCHES_PER_ROOM: int = 3      # Max torches placed on a single room's walls

# ---------------------------------------------------------------------------
# Player combat (unarmed)
# ---------------------------------------------------------------------------
UNARMED_DICE: int = 1         # 1d4 unarmed damage
UNARMED_SIDES: int = 4

# Varied unarmed attack verbs — picked at random to keep combat prose lively.
UNARMED_VERBS: list[str] = [
    "punch",
    "karate-chop",
    "jab",
    "uppercut",
    "elbow",
    "pummel",
    "smack",
    "slug",
    "sock",
    "wallop",
    "clobber",
    "thwack",
]

# Verbs for killing blows — past tense, emphatic.
UNARMED_KILL_VERBS: list[str] = [
    "obliterate",
    "destroy",
    "finish off",
    "lay out",
    "flatten",
    "cream",
    "demolish",
    "pulverize",
]

# ---------------------------------------------------------------------------
# Noise system — actions emit sound, monsters hear it, player hears monsters
# ---------------------------------------------------------------------------
NOISE_WALK: int = 5                 # Sound from a normal walking step
NOISE_RUN: int = 15                 # Sound from a running step (much louder)
NOISE_DROP: int = 3                 # Sound from dropping an item (thud)
NOISE_KICK: int = 20                # Sound from kicking a door (crash, very loud)
NOISE_MELEE: int = 8                # Sound from a melee hit (grunts and impact)
NOISE_MONSTER_MOVE: int = 4         # Default monster footstep noise

NOISE_WALL_ATTENUATION: int = 4     # Extra attenuation per wall or closed door
NOISE_FAINT_THRESHOLD: float = 1.0  # Minimum audible level
NOISE_LOUD_THRESHOLD: float = 8.0   # Above this counts as "loud"

# ---------------------------------------------------------------------------
# Terminal layout
# ---------------------------------------------------------------------------
MIN_TERMINAL_COLS: int = 120
SIDEBAR_GAP: int = 1
