# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""Room definition and random initialization for dungeon generation."""

from __future__ import annotations

__version__ = "0.1.0"

import random

from game.coordinate import Coordinate
from game.constants import (
    BOARD_COLUMNS,
    BOARD_ROWS,
    MIN_ROOM_WIDTH,
    MAX_ROOM_WIDTH,
    MIN_ROOM_HEIGHT,
    MAX_ROOM_HEIGHT,
)


class Room:
    """A rectangular region in the dungeon.

    Rooms start as (top-left, bottom-right) bounding boxes.
    The Board fills, encloses, and connects them.
    """

    __slots__ = ("tl", "br", "room_number", "has_been_mapped", "_centroid")

    def __init__(self) -> None:
        self.tl: Coordinate = Coordinate()
        self.br: Coordinate = Coordinate()
        self.room_number: int = 0
        self.has_been_mapped: bool = False
        self._centroid: Coordinate = Coordinate()

    def initialize(self, rn: int, rng: random.Random) -> None:
        """Randomize the room bounds within the board, guaranteeing fit.

        Args:
            rn:  Room index (used as temporary fill digit).
            rng: Seeded random source for reproducibility.
        """
        self.room_number = rn
        w: int = rng.randint(MIN_ROOM_WIDTH, MAX_ROOM_WIDTH)
        h: int = rng.randint(MIN_ROOM_HEIGHT, MAX_ROOM_HEIGHT)
        self.tl.c = rng.randint(1, BOARD_COLUMNS - w - 1)
        self.tl.r = rng.randint(1, BOARD_ROWS - h - 1)
        self.br.c = self.tl.c + w
        self.br.r = self.tl.r + h
        self._centroid.c = (self.tl.c + self.br.c) // 2
        self._centroid.r = (self.tl.r + self.br.r) // 2
        self.has_been_mapped = False

    def get_centroid(self) -> Coordinate:
        """Return the cached center point of the room."""
        return Coordinate(self._centroid.r, self._centroid.c)
