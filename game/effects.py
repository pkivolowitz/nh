# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""Ephemeral tile effects — fire, scorch marks, and future elements.

Effects are temporary overlays on board cells.  They persist for a
fixed number of turns, interact with creatures that enter them, and
render visually on the board.  The engine ticks them down each turn.

Design
------
- Effects live on the Board in a dict keyed by Coordinate.
- Each turn the engine calls ``board.tick_effects()`` which decrements
  durations, applies per-turn damage, and removes expired effects.
- The renderer draws active effects over the normal cell display.
- Fire effects burn doors open, damage creatures, and illuminate.
"""

from __future__ import annotations

__version__ = "0.1.0"

from enum import IntEnum, auto
from typing import Optional

from game.coordinate import Coordinate


class EffectType(IntEnum):
    """Types of ephemeral tile effects."""
    FIRE = 0           # Active flames — damages, illuminates, burns doors.
    SCORCH = auto()    # Residue after fire fades — cosmetic, dims over time.
    # Future: WATER, ICE, WIND, RUBBLE, etc.


# Visual symbols for effects — cycled for animation.
FIRE_SYMBOLS: list[int] = [ord("^"), ord("*"), ord("~")]
SCORCH_SYMBOL: int = ord(".")

# Duration in turns.
FIRE_DURATION: int = 4          # Active flames persist for 4 turns.
SCORCH_DURATION: int = 8        # Scorch marks linger after fire dies.

# Damage per turn to creatures standing in fire.
FIRE_DAMAGE_PER_TURN: int = 2


class TileEffect:
    """One ephemeral effect on a single board cell."""

    __slots__ = ("effect_type", "pos", "turns_remaining", "damage_per_turn")

    def __init__(self, effect_type: EffectType, pos: Coordinate,
                 turns_remaining: int, damage_per_turn: int = 0) -> None:
        self.effect_type: EffectType = effect_type
        self.pos: Coordinate = pos
        self.turns_remaining: int = turns_remaining
        self.damage_per_turn: int = damage_per_turn

    @property
    def is_expired(self) -> bool:
        """True when the effect should be removed."""
        return self.turns_remaining <= 0

    def tick(self) -> None:
        """Advance one turn."""
        self.turns_remaining -= 1

    @property
    def symbol(self) -> int:
        """Visual symbol for rendering, cycled for fire animation."""
        if self.effect_type == EffectType.FIRE:
            # Cycle through symbols based on remaining turns for flicker.
            return FIRE_SYMBOLS[self.turns_remaining % len(FIRE_SYMBOLS)]
        return SCORCH_SYMBOL
