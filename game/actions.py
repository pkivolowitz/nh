# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""Discrete action and direction enums for the game and ML agent interface."""

from __future__ import annotations

__version__ = "0.1.0"

from enum import IntEnum, auto


class Direction(IntEnum):
    """Eight compass directions plus a sentinel."""
    NONE = 0
    N = auto()
    S = auto()
    E = auto()
    W = auto()
    NE = auto()
    NW = auto()
    SE = auto()
    SW = auto()


# (delta_row, delta_col) for each direction.
DIRECTION_DELTA: dict[Direction, tuple[int, int]] = {
    Direction.NONE: (0, 0),
    Direction.N:    (-1,  0),
    Direction.S:    ( 1,  0),
    Direction.E:    ( 0,  1),
    Direction.W:    ( 0, -1),
    Direction.NE:   (-1,  1),
    Direction.NW:   (-1, -1),
    Direction.SE:   ( 1,  1),
    Direction.SW:   ( 1, -1),
}

# vi-key (lowercase) → Direction mapping.
VI_KEY_TO_DIRECTION: dict[str, Direction] = {
    "k": Direction.N,
    "j": Direction.S,
    "l": Direction.E,
    "h": Direction.W,
    "u": Direction.NE,
    "y": Direction.NW,
    "n": Direction.SE,
    "b": Direction.SW,
}


class Action(IntEnum):
    """Every discrete action a player or AI agent can take.

    Movement actions correspond 1-to-1 with Direction values.
    Parameterized actions (DROP, OPEN_DOOR, CLOSE_DOOR) carry
    a payload in the engine's step() call.
    """
    WAIT = 0

    # Movement (one step).
    MOVE_N = auto()
    MOVE_S = auto()
    MOVE_E = auto()
    MOVE_W = auto()
    MOVE_NE = auto()
    MOVE_NW = auto()
    MOVE_SE = auto()
    MOVE_SW = auto()

    # Stair traversal.
    STAIRS_DOWN = auto()
    STAIRS_UP = auto()

    # Item interaction.
    PICKUP = auto()
    DROP = auto()          # Needs inventory letter parameter.

    # Door interaction.
    OPEN_DOOR = auto()     # Needs direction parameter.
    CLOSE_DOOR = auto()    # Needs direction parameter.
    KICK_DOOR = auto()     # Needs direction parameter.

    # Magic.
    CAST = auto()          # Needs school and direction parameters.
    READ = auto()          # Needs inventory letter parameter.

    # Ranged attack: throw a rock at a target or in a direction.
    THROW_ROCK = auto()    # Takes direction or target_pos kwarg.

    # Consume food for HP restore.
    EAT = auto()           # Takes inventory letter parameter.

    # Drill a magic school: spend concentration, gain XP, no target.
    PRACTICE = auto()      # Takes optional school kwarg.


# Convenience: Direction → movement Action.
DIRECTION_TO_ACTION: dict[Direction, Action] = {
    Direction.N:  Action.MOVE_N,
    Direction.S:  Action.MOVE_S,
    Direction.E:  Action.MOVE_E,
    Direction.W:  Action.MOVE_W,
    Direction.NE: Action.MOVE_NE,
    Direction.NW: Action.MOVE_NW,
    Direction.SE: Action.MOVE_SE,
    Direction.SW: Action.MOVE_SW,
}

# Reverse: movement Action → Direction.
ACTION_TO_DIRECTION: dict[Action, Direction] = {
    v: k for k, v in DIRECTION_TO_ACTION.items()
}
