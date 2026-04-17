# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""Cell types, door states, and the Cell structure that fills the board grid."""

from __future__ import annotations

__version__ = "0.1.0"

from enum import IntEnum


class CellBaseType(IntEnum):
    """Primary classification of a board tile."""
    EMPTY = 0
    ROOM = 1
    CORRIDOR = 2
    WALL = 3
    DOOR = 4


class DoorState(IntEnum):
    """Physical state of a door cell.

    DOOR_NONE is 0 so default-constructed cells are "not a door".
    """
    DOOR_NONE = 0
    DOOR_MISSING = 1    # Archway — always passable.
    DOOR_OPEN = 2       # Passable, doesn't block LOS.
    DOOR_CLOSED = 3     # Blocks movement and LOS.
    DOOR_LOCKED = 4     # Must unlock or kick.
    DOOR_STUCK = 5      # Must force open or kick.
    # DOOR_CHARRED was here briefly — replaced by Cell.door_charred flag
    # so a charred door retains its open/closed state.


class Cell:
    """One tile on the dungeon board.

    ``original_c`` and ``display_c`` store the game-engine display
    constant (see constants.py) or an ASCII ordinal.  The renderer
    maps these to actual curses characters at draw time.
    """

    __slots__ = (
        "base_type",
        "original_c",
        "display_c",
        "final_room_number",
        "has_been_flattened",
        "has_been_added_to_work_list",
        "is_known",
        "lit",
        "door_state",
        "door_horizontal",
        "door_kicks_remaining",
        "door_charred",
    )

    def __init__(self) -> None:
        self.base_type: CellBaseType = CellBaseType.EMPTY
        self.original_c: int = 0
        self.display_c: int = 0
        self.final_room_number: int = 0
        self.has_been_flattened: bool = False
        self.has_been_added_to_work_list: bool = False
        self.is_known: bool = False
        self.lit: bool = False
        self.door_state: DoorState = DoorState.DOOR_NONE
        self.door_horizontal: bool = False
        self.door_kicks_remaining: int = 0
        self.door_charred: bool = False
