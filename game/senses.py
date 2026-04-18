# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""The six senses of every organism in PNH.

Every creature — player, monster, NPC — has a Senses object describing
its perceptual abilities across six axes.  Vision splits into lighted
and unlighted sub-senses because darkvision is a distinct faculty.

Scale
-----
Humans are the unit of measurement: a human has every sense at **1.0**.
Other organisms are rated relative to humans.  A jackal with
``sight_dark=4.0`` perceives four times further in darkness than a
human does.  A factor of ``0.0`` means the sense is absent.

Absolute radii are computed by multiplying the factor by the sense's
base unit (below).  The base unit is what "human-grade" means for that
sense, in game terms.
"""

from __future__ import annotations

__version__ = "0.1.0"

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Base units — what a factor of 1.0 corresponds to, in cells or multiplier.
# ---------------------------------------------------------------------------

# Sight in a lit cell: humans see across a well-lit room.
BASE_SIGHT_LIT: float = 6.0

# Sight in an unlit cell: humans are nearly blind — only what's touching.
BASE_SIGHT_DARK: float = 1.0

# Hearing: multiplier on noise-level thresholds.  Higher factor means
# the organism picks up fainter sounds.  A factor of 2.0 effectively
# halves the faint/loud thresholds for this organism.
BASE_HEARING: float = 1.0

# Smell: human olfaction is essentially useless at range, so the base
# unit is small.  Creatures with real noses have factors in the single
# digits for a range of ~8-16 cells.
BASE_SMELL: float = 2.0

# Touch: adjacent tactile.  Whiskers, air-displacement, proprioception —
# anything that senses what's right next to you without seeing it.
BASE_TOUCH: float = 1.0

# ESP: extrasensory presence detection.  Penetrates walls and light.
# Human "someone's watching me" intuition is 0.5 cells — barely there.
BASE_ESP: float = 0.5


@dataclass
class Senses:
    """Perceptual profile of an organism, scaled against humans (= 1.0).

    All fields default to 1.0 so a bare ``Senses()`` is a human.  Set
    a field to 0.0 to denote an absent sense.
    """

    sight_lit: float = 1.0
    sight_dark: float = 1.0
    hearing: float = 1.0
    smell: float = 1.0
    touch: float = 1.0
    esp: float = 1.0

    def sight_radius(self, target_lit: bool) -> float:
        """Effective sight radius when looking at a *target_lit* cell.

        The lighting of the *target* matters — you need photons at the
        object, not at the viewer — so pass in whether the observed
        cell is illuminated.
        """
        factor: float = self.sight_lit if target_lit else self.sight_dark
        base: float = BASE_SIGHT_LIT if target_lit else BASE_SIGHT_DARK
        return factor * base

    def smell_radius(self) -> float:
        """Directional scent range, in cells.  Penetrates walls."""
        return self.smell * BASE_SMELL

    def touch_radius(self) -> float:
        """Tactile detection range, in cells.  Usually 1.0 (adjacent)."""
        return self.touch * BASE_TOUCH

    def esp_radius(self) -> float:
        """ESP presence-detection range, in cells.  Ignores walls."""
        return self.esp * BASE_ESP

    def hearing_threshold_scale(self) -> float:
        """Multiplier on noise-level thresholds.  < 1.0 means sharper.

        A creature with hearing factor 2.0 has noise thresholds at 1/2
        the baseline — it picks up sounds twice as quiet as a human.
        """
        if self.hearing <= 0:
            return float("inf")
        return BASE_HEARING / self.hearing


# Human baseline — the unit organism.  Kept as a module-level constant
# so every non-monster actor can default to it without repeating the
# fields.
HUMAN_SENSES: Senses = Senses()
