# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""Fire school spell resolution.

Fire is the first fully implemented school.  Casting fire produces
effects scaled by proficiency:

- **Novice**: wild burst — random radius, random direction, may hit
  the caster.  Terrifying and unpredictable.
- **Apprentice**: aimed but sloppy — hits the target area but with
  spread.  Collateral damage.
- **Journeyman**: directed flame — reliable damage in a cone or at
  a single target.
- **Expert**: shaped fire — precise area control, can target a single
  cell without splash.
- **Master**: surgical flame — can relight a wall torch without
  scorching the stone, or thread a flame through a doorway.

Monsters in the blast zone take damage.  The noise from fire draws
attention.  Jackals and other creatures with persistent brains will
learn over many games that fire means danger and scatter.
"""

from __future__ import annotations

__version__ = "0.1.0"

import random
from typing import TYPE_CHECKING, Optional

from game.actions import Direction, DIRECTION_DELTA
from game.brain import REWARD_DEATH, REWARD_FIRE_NEAR, REWARD_FIRE_DAMAGE
from game.constants import BOARD_ROWS, BOARD_COLUMNS
from game.coordinate import Coordinate
from game.magic import (
    CastResult, CastOutcome, ProficiencyTier, MagicSchool,
)

if TYPE_CHECKING:
    from game.engine import GameEngine

# ---------------------------------------------------------------------------
# Fire constants
# ---------------------------------------------------------------------------

# Base damage at each tier (before outcome modifiers).
FIRE_BASE_DAMAGE: dict[ProficiencyTier, int] = {
    ProficiencyTier.NOVICE: 4,
    ProficiencyTier.APPRENTICE: 6,
    ProficiencyTier.JOURNEYMAN: 8,
    ProficiencyTier.EXPERT: 10,
    ProficiencyTier.MASTER: 12,
}

# Blast radius at each tier (cells from target center).
# Higher proficiency = tighter control (smaller if desired).
FIRE_MAX_RADIUS: dict[ProficiencyTier, int] = {
    ProficiencyTier.NOVICE: 3,       # Uncontrolled — big and dangerous.
    ProficiencyTier.APPRENTICE: 2,
    ProficiencyTier.JOURNEYMAN: 2,
    ProficiencyTier.EXPERT: 1,
    ProficiencyTier.MASTER: 0,       # Can hit a single cell.
}

# Noise level from fire casting (all tiers are loud).
FIRE_NOISE: int = 18
FIRE_NOISE_DESC: str = "a roar of flames"

# Range: how far from the caster fire can reach.
FIRE_RANGE: dict[ProficiencyTier, int] = {
    ProficiencyTier.NOVICE: 2,
    ProficiencyTier.APPRENTICE: 3,
    ProficiencyTier.JOURNEYMAN: 5,
    ProficiencyTier.EXPERT: 7,
    ProficiencyTier.MASTER: 9,
}

# ---------------------------------------------------------------------------
# Flavor messages
# ---------------------------------------------------------------------------

_CLEAN_MESSAGES: list[str] = [
    "Flame erupts exactly where you willed it!",
    "Fire leaps from your hands with perfect precision.",
    "A jet of fire strikes true.",
]

_PARTIAL_MESSAGES: list[str] = [
    "Flames lick the target but without full force.",
    "The fire reaches the mark, weakened by the distance.",
    "A tongue of flame — not your best work, but it connects.",
]

_WILD_MESSAGES: list[str] = [
    "Fire explodes outward in every direction!",
    "The flame tears free of your control and rages wild!",
    "A gout of fire sprays across the room!",
]

_MISFIRE_MESSAGES: list[str] = [
    "The fire veers off — that wasn't where you aimed!",
    "Flames swerve and strike the wrong spot entirely!",
    "The fire has a mind of its own!",
]

_FIZZLE_MESSAGES: list[str] = [
    "A few sparks dance from your fingers and die.",
    "You feel the heat rise... then nothing.",
    "Smoke curls from your palm. That's it.",
    "A puff of warm air. The fire refuses to come.",
]

_BACKFIRE_MESSAGES: list[str] = [
    "The fire turns inward — you burn yourself!",
    "Flame rebounds from nowhere and engulfs your hands!",
    "The spell collapses — fire erupts at your feet!",
]

# Master-tier special: relighting a torch.
_KINDLE_MESSAGE: str = ("You extend a thread of flame — the torch "
                         "catches and burns again.")


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------

def resolve_fire(engine: GameEngine, direction: Direction,
                 tier: ProficiencyTier, outcome: CastOutcome,
                 rng: random.Random) -> CastResult:
    """Resolve a fire cast and apply effects to the game world.

    Args:
        engine: The game engine (for board access, damage application).
        direction: Where the player aimed.
        tier: Current proficiency tier in fire.
        outcome: The pre-rolled cast outcome.
        rng: Seeded random source.

    Returns:
        A CastResult with all details for the engine to report.
    """
    result: CastResult = CastResult()
    result.school = MagicSchool.FIRE
    result.outcome = outcome
    result.noise_level = FIRE_NOISE
    result.noise_desc = FIRE_NOISE_DESC

    player_pos: Coordinate = engine.player.pos

    if outcome == CastOutcome.FIZZLE:
        result.message = rng.choice(_FIZZLE_MESSAGES)
        result.noise_level = 3  # Barely audible puff.
        result.noise_desc = "a faint sizzle"
        return result

    if outcome == CastOutcome.BACKFIRE:
        result.message = rng.choice(_BACKFIRE_MESSAGES)
        dmg: int = max(1, FIRE_BASE_DAMAGE[tier] // 2)
        result.damage_taken = dmg
        result.target_pos = (player_pos.r, player_pos.c)
        return result

    # Determine target center based on outcome.
    dr, dc = DIRECTION_DELTA.get(direction, (0, 0))
    fire_range: int = FIRE_RANGE[tier]

    if outcome == CastOutcome.MISFIRE:
        # Random adjacent direction instead of intended.
        dirs = [d for d in Direction if d != Direction.NONE]
        misfire_dir: Direction = rng.choice(dirs)
        dr, dc = DIRECTION_DELTA[misfire_dir]
        result.message = rng.choice(_MISFIRE_MESSAGES)
    elif outcome == CastOutcome.WILD:
        result.message = rng.choice(_WILD_MESSAGES)
    elif outcome == CastOutcome.PARTIAL:
        result.message = rng.choice(_PARTIAL_MESSAGES)
        fire_range = max(1, fire_range // 2)
    elif outcome == CastOutcome.CLEAN:
        result.message = rng.choice(_CLEAN_MESSAGES)

    # Target center: walk fire_range steps in direction from player.
    target_r: int = player_pos.r + dr * fire_range
    target_c: int = player_pos.c + dc * fire_range
    target_r = max(0, min(BOARD_ROWS - 1, target_r))
    target_c = max(0, min(BOARD_COLUMNS - 1, target_c))
    result.target_pos = (target_r, target_c)

    # Determine blast radius.
    if outcome == CastOutcome.WILD:
        # Wild: use max uncontrolled radius.
        radius: int = FIRE_MAX_RADIUS[ProficiencyTier.NOVICE]
    elif outcome == CastOutcome.MISFIRE:
        radius = FIRE_MAX_RADIUS[tier]
    elif outcome == CastOutcome.PARTIAL:
        radius = FIRE_MAX_RADIUS[tier]
    else:
        radius = FIRE_MAX_RADIUS[tier]

    # Determine base damage.
    base_dmg: int = FIRE_BASE_DAMAGE[tier]
    if outcome == CastOutcome.PARTIAL:
        base_dmg = max(1, base_dmg * 2 // 3)
    elif outcome == CastOutcome.WILD:
        # Wild does full damage but to unintended area.
        pass

    # Apply damage to monsters in the blast zone.
    total_dealt: int = 0
    kills: list[str] = []
    hit_monsters: list[str] = []

    for mr in range(target_r - radius, target_r + radius + 1):
        for mc in range(target_c - radius, target_c + radius + 1):
            if not (0 <= mr < BOARD_ROWS and 0 <= mc < BOARD_COLUMNS):
                continue
            # Distance from blast center — damage falls off.
            dist: int = abs(mr - target_r) + abs(mc - target_c)
            if dist > radius:
                continue
            cell_dmg: int = max(1, base_dmg - dist * 2)

            pos: Coordinate = Coordinate(mr, mc)
            # Place fire on the board — visible, persistent, interactive.
            engine.board.add_fire(pos)
            monster = engine.board.get_monster_at(pos)
            if monster is not None:
                actual: int = monster.take_damage(cell_dmg)
                total_dealt += actual
                brain = monster.species.get_brain()
                if not monster.is_alive:
                    if monster.last_action is not None:
                        brain.record_outcome(
                            monster, monster.last_action, REWARD_DEATH, engine
                        )
                    engine.board.remove_monster(pos)
                    kills.append(monster.name)
                else:
                    hit_monsters.append(monster.name)
                    # Shaping reward: took fire damage but survived.
                    # Teaches the brain that being near fire is painful
                    # even when you don't die.
                    if monster.last_action is not None:
                        brain.record_outcome(
                            monster, monster.last_action,
                            REWARD_FIRE_DAMAGE, engine
                        )

            # Self-damage if player is in the blast zone (wild/misfire).
            if pos == player_pos and outcome in (CastOutcome.WILD,
                                                  CastOutcome.MISFIRE):
                self_dmg: int = max(1, cell_dmg // 2)
                result.damage_taken += self_dmg

    result.damage_dealt = total_dealt

    # Shaping reward for monsters near the blast but not hit.
    # Being adjacent to an explosion is terrifying even if you
    # weren't in the direct blast — teaches avoidance before death.
    fear_radius: int = radius + 2
    for mr in range(target_r - fear_radius, target_r + fear_radius + 1):
        for mc in range(target_c - fear_radius, target_c + fear_radius + 1):
            if not (0 <= mr < BOARD_ROWS and 0 <= mc < BOARD_COLUMNS):
                continue
            dist = abs(mr - target_r) + abs(mc - target_c)
            if dist <= radius or dist > fear_radius:
                continue  # Already handled above, or too far.
            pos = Coordinate(mr, mc)
            monster = engine.board.get_monster_at(pos)
            if monster is not None and monster.is_alive:
                brain = monster.species.get_brain()
                if monster.last_action is not None:
                    brain.record_outcome(
                        monster, monster.last_action,
                        REWARD_FIRE_NEAR, engine
                    )

    # Append kill/hit info to the message.
    if kills:
        kill_str: str = ", ".join(kills)
        result.message += f" The flames consume the {kill_str}!"
    elif hit_monsters:
        hit_str: str = ", ".join(hit_monsters)
        result.message += f" Fire scorches the {hit_str}."

    return result
