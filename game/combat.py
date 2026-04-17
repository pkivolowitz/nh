# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""Combat system: extensible OO hierarchy for attack resolution.

The base class ``CombatAction`` defines the interface.  Subclasses
implement specific attack types -- melee bump, ranged, spell, etc.
The combat action resolves mechanics only; message formatting is the
engine's responsibility so it can use proper pronouns.
"""

from __future__ import annotations

__version__ = "0.1.0"

import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.creature import Creature


class CombatResult:
    """Raw outcome of a single combat action -- no display strings."""

    __slots__ = ("hit", "damage", "defender_killed")

    def __init__(self, hit: bool, damage: int,
                 defender_killed: bool) -> None:
        self.hit: bool = hit
        self.damage: int = damage
        self.defender_killed: bool = defender_killed


class CombatAction(ABC):
    """Base class for all combat actions."""

    @abstractmethod
    def execute(self, attacker: Creature, defender: Creature,
                rng: random.Random) -> CombatResult:
        """Resolve this action and apply effects to *defender*."""
        ...

    @abstractmethod
    def describe(self) -> str:
        """Human-readable description (e.g. 'bites (1d2)')."""
        ...


class BumpAttack(CombatAction):
    """Melee attack triggered by bumping into a creature.

    Damage is rolled as *dice* d *sides* (e.g. 1d2 for a jackal bite).
    """

    def __init__(self, dice: int, sides: int, verb: str = "hits") -> None:
        self.dice: int = dice
        self.sides: int = sides
        self.verb: str = verb

    def execute(self, attacker: Creature, defender: Creature,
                rng: random.Random,
                damage_bonus: int = 0) -> CombatResult:
        """Roll damage dice, add *damage_bonus*, and apply to *defender*."""
        damage: int = sum(
            rng.randint(1, self.sides) for _ in range(self.dice)
        ) + damage_bonus
        if damage < 0:
            damage = 0
        actual: int = defender.take_damage(damage)
        return CombatResult(
            hit=True,
            damage=actual,
            defender_killed=not defender.is_alive,
        )

    def describe(self) -> str:
        """Human-readable description."""
        return f"{self.verb} ({self.dice}d{self.sides})"
