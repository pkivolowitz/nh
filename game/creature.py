# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""Base class for all living entities -- players and monsters alike.

The energy accumulator drives the speed-based turn system: each tick
a creature gains ``speed`` energy and acts when energy reaches the
threshold.
"""

from __future__ import annotations

__version__ = "0.1.0"

from game.coordinate import Coordinate


class Creature:
    """A living entity with position, health, speed, and display properties.

    Both Player and Monster inherit from this class, ensuring a unified
    interface for combat, rendering, and ML observation.
    """

    def __init__(self, name: str, pos: Coordinate, speed: int,
                 max_hp: int, symbol: int, color_pair: int) -> None:
        self.name: str = name
        self.pos: Coordinate = pos
        self.speed: int = speed
        self.hp: int = max_hp
        self.max_hp: int = max_hp
        self.symbol: int = symbol
        self.color_pair: int = color_pair
        self.is_alive: bool = True
        self.energy: int = 0

    def take_damage(self, amount: int) -> int:
        """Apply *amount* damage.  Returns actual damage dealt.

        Clamps HP to zero and marks the creature dead when HP is
        exhausted.
        """
        actual: int = min(amount, self.hp)
        self.hp -= actual
        if self.hp <= 0:
            self.hp = 0
            self.is_alive = False
        return actual

    def heal(self, amount: int) -> int:
        """Restore up to *amount* HP.  Returns actual HP restored."""
        room: int = self.max_hp - self.hp
        actual: int = min(amount, room)
        self.hp += actual
        return actual

    def get_state(self) -> dict:
        """Machine-readable snapshot for the ML observation interface."""
        return {
            "name": self.name,
            "pos": self.pos.to_tuple(),
            "hp": self.hp,
            "max_hp": self.max_hp,
            "speed": self.speed,
            "is_alive": self.is_alive,
        }
