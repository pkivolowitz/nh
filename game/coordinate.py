# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""Grid coordinate with arithmetic, distance, and interpolation."""

from __future__ import annotations

__version__ = "0.1.0"

import math


class Coordinate:
    """Integer (row, col) position on the board.

    Supports vector arithmetic, Euclidean distance, and linear
    interpolation — the same operations the C++ version provides.
    Hashable so it can serve as a dict key (e.g. goodies map).
    """

    __slots__ = ("r", "c")

    def __init__(self, r: int = 0, c: int = 0) -> None:
        self.r: int = r
        self.c: int = c

    # -- arithmetic --------------------------------------------------------

    def __add__(self, other: Coordinate) -> Coordinate:
        return Coordinate(self.r + other.r, self.c + other.c)

    def __sub__(self, other: Coordinate) -> Coordinate:
        return Coordinate(self.r - other.r, self.c - other.c)

    def __mul__(self, t: float) -> Coordinate:
        return Coordinate(int(self.r * t), int(self.c * t))

    def __rmul__(self, t: float) -> Coordinate:
        return self.__mul__(t)

    # -- comparison / hashing ----------------------------------------------

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Coordinate):
            return NotImplemented
        return self.r == other.r and self.c == other.c

    def __ne__(self, other: object) -> bool:
        if not isinstance(other, Coordinate):
            return NotImplemented
        return self.r != other.r or self.c != other.c

    def __hash__(self) -> int:
        return hash((self.r, self.c))

    def __lt__(self, other: Coordinate) -> bool:
        """Ordering needed for sorted containers (mirrors C++ operator<)."""
        if self.r != other.r:
            return self.r < other.r
        return self.c < other.c

    # -- geometry ----------------------------------------------------------

    def distance(self, other: Coordinate) -> float:
        """Euclidean distance to *other*."""
        dr = self.r - other.r
        dc = self.c - other.c
        return math.sqrt(dr * dr + dc * dc)

    def lerp(self, other: Coordinate, t: float) -> Coordinate:
        """Linear interpolation toward *other* at parameter *t* in [0, 1]."""
        delta = Coordinate(other.r - self.r, other.c - self.c)
        return delta * t + self

    def is_neighbor(self, other: Coordinate) -> bool:
        """True if *other* is orthogonally or diagonally adjacent."""
        return abs(self.r - other.r) <= 1 and abs(self.c - other.c) <= 1

    # -- display -----------------------------------------------------------

    def __repr__(self) -> str:
        return f"Coordinate(r={self.r}, c={self.c})"

    def to_tuple(self) -> tuple[int, int]:
        """Return (row, col) as a plain tuple."""
        return (self.r, self.c)
