# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""Magic system: schools, proficiency, concentration, and spell resolution.

Design
------
There are no named spells.  You learn to manipulate an *element*
(fire, water, air, earth) or a *discipline* (healing, teleportation,
force).  Reading a spellbook either teaches the school (first book) or
adds proficiency (subsequent books in the same school).

Proficiency grows with every cast and determines:
- How precisely you can shape the effect.
- How much concentration each cast costs (experts are more efficient).
- The probability distribution across outcome tiers (clean → wild → backfire).

Concentration is the casting resource.  It regenerates over time,
governed by Intelligence (paralleling HP regen governed by Constitution).
"""

from __future__ import annotations

__version__ = "0.1.0"

import logging
import random
from enum import IntEnum, auto
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from game.engine import GameEngine

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schools
# ---------------------------------------------------------------------------

class MagicSchool(IntEnum):
    """Elemental and discipline schools of magic."""
    FIRE = 0
    WATER = auto()
    AIR = auto()
    EARTH = auto()
    HEALING = auto()
    TELEPORT = auto()
    FORCE = auto()


# Human-readable names and casting verbs.
SCHOOL_NAMES: dict[MagicSchool, str] = {
    MagicSchool.FIRE: "Fire",
    MagicSchool.WATER: "Water",
    MagicSchool.AIR: "Air",
    MagicSchool.EARTH: "Earth",
    MagicSchool.HEALING: "Healing",
    MagicSchool.TELEPORT: "Teleportation",
    MagicSchool.FORCE: "Force",
}

SCHOOL_CAST_VERBS: dict[MagicSchool, str] = {
    MagicSchool.FIRE: "invoke fire",
    MagicSchool.WATER: "call upon water",
    MagicSchool.AIR: "summon the wind",
    MagicSchool.EARTH: "command the stone",
    MagicSchool.HEALING: "channel healing energy",
    MagicSchool.TELEPORT: "bend space",
    MagicSchool.FORCE: "unleash force",
}

# Hotkeys for school selection during casting (displayed to player).
SCHOOL_HOTKEYS: dict[str, MagicSchool] = {
    "f": MagicSchool.FIRE,
    "w": MagicSchool.WATER,
    "a": MagicSchool.AIR,
    "e": MagicSchool.EARTH,
    "h": MagicSchool.HEALING,
    "t": MagicSchool.TELEPORT,
    "r": MagicSchool.FORCE,
}


# ---------------------------------------------------------------------------
# Proficiency tiers — named thresholds for display and effect scaling
# ---------------------------------------------------------------------------

class ProficiencyTier(IntEnum):
    """Named proficiency levels for UI display and effect scaling."""
    NOVICE = 0       # Just learned; wild, unpredictable.
    APPRENTICE = 1   # Some control; still dangerous.
    JOURNEYMAN = 2   # Reliable but not refined.
    EXPERT = 3       # Precise and efficient.
    MASTER = 4       # Surgical control, minimal waste.

# XP thresholds for each tier.  Earned 1 XP per cast, plus bonus XP
# from reading additional spellbooks in the same school.
TIER_THRESHOLDS: dict[ProficiencyTier, int] = {
    ProficiencyTier.NOVICE: 0,
    ProficiencyTier.APPRENTICE: 10,
    ProficiencyTier.JOURNEYMAN: 30,
    ProficiencyTier.EXPERT: 70,
    ProficiencyTier.MASTER: 150,
}

TIER_NAMES: dict[ProficiencyTier, str] = {
    ProficiencyTier.NOVICE: "Novice",
    ProficiencyTier.APPRENTICE: "Apprentice",
    ProficiencyTier.JOURNEYMAN: "Journeyman",
    ProficiencyTier.EXPERT: "Expert",
    ProficiencyTier.MASTER: "Master",
}

# XP bonus from reading an additional spellbook in a known school.
SPELLBOOK_XP_BONUS: int = 8


# ---------------------------------------------------------------------------
# Concentration costs — decrease with proficiency
# ---------------------------------------------------------------------------

# Base concentration cost per school (at Novice tier).
SCHOOL_BASE_COST: dict[MagicSchool, int] = {
    MagicSchool.FIRE: 5,
    MagicSchool.WATER: 4,
    MagicSchool.AIR: 4,
    MagicSchool.EARTH: 5,
    MagicSchool.HEALING: 6,
    MagicSchool.TELEPORT: 8,
    MagicSchool.FORCE: 5,
}

# Discount per tier (subtracted from base cost, floored at 1).
TIER_COST_DISCOUNT: dict[ProficiencyTier, int] = {
    ProficiencyTier.NOVICE: 0,
    ProficiencyTier.APPRENTICE: 1,
    ProficiencyTier.JOURNEYMAN: 2,
    ProficiencyTier.EXPERT: 3,
    ProficiencyTier.MASTER: 4,
}


# ---------------------------------------------------------------------------
# Concentration regeneration
# ---------------------------------------------------------------------------

# Parallels HP regen: INT 18 → every CONC_BASE_INTERVAL turns,
# INT 12 → every CONC_BASE_INTERVAL + (18-12)*CONC_INT_SCALE//3 turns.
CONC_BASE_INTERVAL: int = 8     # Turns between conc regen at max INT (18)
CONC_INT_SCALE: int = 8         # Numerator of per-point penalty (divided by 3)


# ---------------------------------------------------------------------------
# Outcome tiers — what happens when you cast
# ---------------------------------------------------------------------------

class CastOutcome(IntEnum):
    """Possible outcomes of a cast attempt, from best to worst."""
    CLEAN = 0        # Intended effect, full control.
    PARTIAL = 1      # Reduced effect but on target.
    WILD = 2         # Effect happens but wrong shape/target/intensity.
    MISFIRE = 3      # Hits random adjacent tile.
    FIZZLE = 4       # Nothing much happens.
    BACKFIRE = 5     # Effect rebounds on the caster.

# Outcome probability weights indexed by proficiency tier.
# Higher tiers shift probability mass toward CLEAN.
OUTCOME_WEIGHTS: dict[ProficiencyTier, dict[CastOutcome, int]] = {
    ProficiencyTier.NOVICE: {
        CastOutcome.CLEAN: 10,
        CastOutcome.PARTIAL: 15,
        CastOutcome.WILD: 25,
        CastOutcome.MISFIRE: 20,
        CastOutcome.FIZZLE: 20,
        CastOutcome.BACKFIRE: 10,
    },
    ProficiencyTier.APPRENTICE: {
        CastOutcome.CLEAN: 25,
        CastOutcome.PARTIAL: 25,
        CastOutcome.WILD: 20,
        CastOutcome.MISFIRE: 15,
        CastOutcome.FIZZLE: 10,
        CastOutcome.BACKFIRE: 5,
    },
    ProficiencyTier.JOURNEYMAN: {
        CastOutcome.CLEAN: 45,
        CastOutcome.PARTIAL: 25,
        CastOutcome.WILD: 15,
        CastOutcome.MISFIRE: 8,
        CastOutcome.FIZZLE: 5,
        CastOutcome.BACKFIRE: 2,
    },
    ProficiencyTier.EXPERT: {
        CastOutcome.CLEAN: 65,
        CastOutcome.PARTIAL: 20,
        CastOutcome.WILD: 8,
        CastOutcome.MISFIRE: 4,
        CastOutcome.FIZZLE: 2,
        CastOutcome.BACKFIRE: 1,
    },
    ProficiencyTier.MASTER: {
        CastOutcome.CLEAN: 80,
        CastOutcome.PARTIAL: 12,
        CastOutcome.WILD: 5,
        CastOutcome.MISFIRE: 2,
        CastOutcome.FIZZLE: 1,
        CastOutcome.BACKFIRE: 0,
    },
}


# ---------------------------------------------------------------------------
# Per-player school state
# ---------------------------------------------------------------------------

class SchoolState:
    """Tracks a player's knowledge and proficiency in one magic school."""

    __slots__ = ("school", "xp", "known")

    def __init__(self, school: MagicSchool) -> None:
        self.school: MagicSchool = school
        self.xp: int = 0
        self.known: bool = False   # True once the first book is read.

    @property
    def tier(self) -> ProficiencyTier:
        """Current proficiency tier based on accumulated XP."""
        result: ProficiencyTier = ProficiencyTier.NOVICE
        for t in ProficiencyTier:
            if self.xp >= TIER_THRESHOLDS[t]:
                result = t
        return result

    @property
    def concentration_cost(self) -> int:
        """Concentration cost for a cast at current proficiency."""
        base: int = SCHOOL_BASE_COST[self.school]
        discount: int = TIER_COST_DISCOUNT[self.tier]
        return max(1, base - discount)

    def add_xp(self, amount: int) -> None:
        """Grant proficiency XP.  Called on cast (1 XP) or book read (bonus)."""
        self.xp += amount


# ---------------------------------------------------------------------------
# SpellKnowledge — container for all schools, lives on the Player
# ---------------------------------------------------------------------------

class SpellKnowledge:
    """Manages the player's magical knowledge across all schools."""

    def __init__(self) -> None:
        self.schools: dict[MagicSchool, SchoolState] = {
            s: SchoolState(s) for s in MagicSchool
        }

    def known_schools(self) -> list[MagicSchool]:
        """Schools the player has learned (read at least one book)."""
        return [s for s, st in self.schools.items() if st.known]

    def learn(self, school: MagicSchool) -> tuple[bool, str]:
        """Learn a school or add proficiency if already known.

        Returns (was_new, message).
        """
        state: SchoolState = self.schools[school]
        name: str = SCHOOL_NAMES[school]
        if not state.known:
            state.known = True
            return True, (f"The book crumbles to dust. "
                          f"You have learned {name}!")
        state.add_xp(SPELLBOOK_XP_BONUS)
        tier_name: str = TIER_NAMES[state.tier]
        return False, (f"The book crumbles to dust. "
                       f"Your {name} deepens. ({tier_name})")


# ---------------------------------------------------------------------------
# Low-concentration flavor messages
# ---------------------------------------------------------------------------

LOW_CONC_MESSAGES: list[str] = [
    "Your thoughts scatter like leaves in the wind.",
    "You struggle to focus — the words slip away.",
    "Your mind is a fog — you can't hold a thought.",
    "Exhaustion clouds your mind. Concentration eludes you.",
    "You reach for the magic but your mind won't grasp it.",
    "A dull ache behind your eyes — you can't concentrate.",
]


# ---------------------------------------------------------------------------
# Cast result
# ---------------------------------------------------------------------------

class CastResult:
    """What actually happened when the player cast a spell."""

    __slots__ = ("outcome", "school", "message", "damage_dealt",
                 "damage_taken", "noise_level", "noise_desc",
                 "target_pos", "concentration_spent")

    def __init__(self) -> None:
        self.outcome: CastOutcome = CastOutcome.FIZZLE
        self.school: MagicSchool = MagicSchool.FIRE
        self.message: str = ""
        self.damage_dealt: int = 0
        self.damage_taken: int = 0
        self.noise_level: int = 0
        self.noise_desc: str = ""
        self.target_pos: Optional[tuple[int, int]] = None
        self.concentration_spent: int = 0


# ---------------------------------------------------------------------------
# Outcome roller
# ---------------------------------------------------------------------------

def roll_outcome(tier: ProficiencyTier, rng: random.Random) -> CastOutcome:
    """Roll a cast outcome based on proficiency tier."""
    weights: dict[CastOutcome, int] = OUTCOME_WEIGHTS[tier]
    outcomes: list[CastOutcome] = list(weights.keys())
    wt: list[int] = [weights[o] for o in outcomes]
    return rng.choices(outcomes, weights=wt, k=1)[0]
