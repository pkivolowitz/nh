# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""Fire school spell resolution.

Fire is the first fully implemented school.  Casting fire produces
effects scaled by proficiency:

- **Novice**: direction only, random distance, random radius.
  Uncontrolled and dangerous to the caster.
- **Apprentice**: cursor-targeted, medium radius (no choice).
  Better aim but no blast control.
- **Journeyman**: cursor-targeted, choose small or medium radius.
- **Expert**: cursor-targeted, choose small, medium, or large.
- **Master**: cursor-targeted, choose small, medium, or large,
  near-perfect accuracy.

Damage falls off with distance from impact center:
    cell_damage = base_damage / (1 + dist²)

Monsters in the blast zone take damage.  The noise from fire draws
attention.  Jackals and other creatures with persistent brains will
learn over many games that fire means danger and scatter.
"""

from __future__ import annotations

__version__ = "0.2.0"

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

# Base damage at each tier (before area falloff).
FIRE_BASE_DAMAGE: dict[ProficiencyTier, int] = {
    ProficiencyTier.NOVICE: 4,
    ProficiencyTier.APPRENTICE: 6,
    ProficiencyTier.JOURNEYMAN: 8,
    ProficiencyTier.EXPERT: 10,
    ProficiencyTier.MASTER: 12,
}

# Radius indices: 0=small (single cell), 1=medium, 2=large.
RADIUS_SMALL: int = 0
RADIUS_MEDIUM: int = 1
RADIUS_LARGE: int = 2

# Actual cell radius for each size.
RADIUS_CELLS: dict[int, int] = {
    RADIUS_SMALL: 0,     # Just the target cell.
    RADIUS_MEDIUM: 1,    # Target + adjacent (up to 9 cells).
    RADIUS_LARGE: 2,     # Two-cell spread (up to 25 cells).
}

RADIUS_NAMES: dict[int, str] = {
    RADIUS_SMALL: "small",
    RADIUS_MEDIUM: "medium",
    RADIUS_LARGE: "large",
}

# Which radius choices each tier unlocks.
# Novice gets no choice (stuck with large — uncontrolled).
# Control grows with proficiency: masters can focus to a single cell.
TIER_RADIUS_CHOICES: dict[ProficiencyTier, list[int]] = {
    ProficiencyTier.NOVICE: [],              # Large, no choice.
    ProficiencyTier.APPRENTICE: [],          # Fixed large, no choice.
    ProficiencyTier.JOURNEYMAN: [RADIUS_LARGE, RADIUS_MEDIUM],
    ProficiencyTier.EXPERT: [RADIUS_LARGE, RADIUS_MEDIUM, RADIUS_SMALL],
    ProficiencyTier.MASTER: [RADIUS_LARGE, RADIUS_MEDIUM, RADIUS_SMALL],
}

# Whether cursor targeting is available at this tier.
TIER_HAS_CURSOR: dict[ProficiencyTier, bool] = {
    ProficiencyTier.NOVICE: False,
    ProficiencyTier.APPRENTICE: True,
    ProficiencyTier.JOURNEYMAN: True,
    ProficiencyTier.EXPERT: True,
    ProficiencyTier.MASTER: True,
}

# Maximum range for fire (same for everyone).
FIRE_MAX_RANGE: int = 7

# Noise level from fire casting (all tiers are loud).
FIRE_NOISE: int = 18
FIRE_NOISE_DESC: str = "a roar of flames"

# Accuracy: chance (0.0-1.0) that the spell hits exactly where aimed.
# On miss, it drifts 1-2 cells in a random direction.
FIRE_ACCURACY: dict[ProficiencyTier, float] = {
    ProficiencyTier.NOVICE: 0.3,
    ProficiencyTier.APPRENTICE: 0.5,
    ProficiencyTier.JOURNEYMAN: 0.7,
    ProficiencyTier.EXPERT: 0.9,
    ProficiencyTier.MASTER: 1.0,
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _trace_to_target(board, origin: Coordinate,
                     target: Coordinate) -> Coordinate:
    """Walk from *origin* toward *target*, stopping at walls.

    Returns the last open cell before hitting a wall, or *target*
    if the path is clear.
    """
    if origin == target:
        return target

    dist: float = origin.distance(target)
    if dist < 1.0:
        return target

    # Step along the ray in small increments.
    steps: int = int(dist) + 1
    prev: Coordinate = origin
    for i in range(1, steps + 1):
        t: float = i / steps
        mid: Coordinate = origin.lerp(target, t)
        cell = board.cells[mid.r][mid.c]
        from game.cell import CellBaseType, DoorState
        door_blocks = (
            cell.base_type == CellBaseType.DOOR
            and cell.door_state not in (DoorState.DOOR_OPEN,
                                        DoorState.DOOR_MISSING)
        )
        if cell.base_type in (CellBaseType.EMPTY, CellBaseType.WALL) or door_blocks:
            return prev
        prev = mid
    return prev


def _apply_drift(rng: random.Random, target: Coordinate,
                 max_drift: int) -> Coordinate:
    """Shift *target* by a random offset of 1 to *max_drift* cells."""
    dr: int = rng.randint(-max_drift, max_drift)
    dc: int = rng.randint(-max_drift, max_drift)
    if dr == 0 and dc == 0:
        dr = rng.choice([-1, 1])
    nr: int = max(0, min(BOARD_ROWS - 1, target.r + dr))
    nc: int = max(0, min(BOARD_COLUMNS - 1, target.c + dc))
    return Coordinate(nr, nc)


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------

def resolve_fire(engine: GameEngine, direction: Direction,
                 tier: ProficiencyTier, outcome: CastOutcome,
                 rng: random.Random, *,
                 target_pos: Optional[Coordinate] = None,
                 chosen_radius: int = -1) -> CastResult:
    """Resolve a fire cast and apply effects to the game world.

    Args:
        engine: The game engine (for board access, damage application).
        direction: Where the player aimed (novice only).
        tier: Current proficiency tier in fire.
        outcome: The pre-rolled cast outcome.
        rng: Seeded random source.
        target_pos: Cursor-selected target cell (None for novice).
        chosen_radius: Player's radius choice (0/1/2) or -1 for
            tier-assigned default.

    Returns:
        A CastResult with all details for the engine to report.
    """
    result: CastResult = CastResult()
    result.school = MagicSchool.FIRE
    result.outcome = outcome
    result.noise_level = FIRE_NOISE
    result.noise_desc = FIRE_NOISE_DESC

    player_pos: Coordinate = engine.player.pos
    board = engine.board

    # -- Fizzle: nothing happens. --
    if outcome == CastOutcome.FIZZLE:
        result.message = rng.choice(_FIZZLE_MESSAGES)
        result.noise_level = 3
        result.noise_desc = "a faint sizzle"
        return result

    # -- Backfire: damage self. --
    if outcome == CastOutcome.BACKFIRE:
        result.message = rng.choice(_BACKFIRE_MESSAGES)
        dmg: int = max(1, FIRE_BASE_DAMAGE[tier] // 2)
        result.damage_taken = dmg
        result.target_pos = (player_pos.r, player_pos.c)
        return result

    # -- Determine impact point. --
    if target_pos is not None:
        # Cursor-targeted (apprentice+).
        aimed_at: Coordinate = target_pos
    else:
        # Novice: direction + random distance.
        dr, dc = DIRECTION_DELTA.get(direction, (0, 0))
        dist: int = rng.randint(1, FIRE_MAX_RANGE)
        aim_r: int = max(0, min(BOARD_ROWS - 1, player_pos.r + dr * dist))
        aim_c: int = max(0, min(BOARD_COLUMNS - 1, player_pos.c + dc * dist))
        aimed_at = Coordinate(aim_r, aim_c)

    # Trace LOS — stop at walls.
    impact: Coordinate = _trace_to_target(board, player_pos, aimed_at)

    # Apply accuracy drift.
    if outcome == CastOutcome.MISFIRE:
        # Misfire: large random drift regardless of tier.
        impact = _apply_drift(rng, impact, 3)
        result.message = rng.choice(_MISFIRE_MESSAGES)
    elif outcome == CastOutcome.WILD:
        # Wild: moderate drift.
        impact = _apply_drift(rng, impact, 2)
        result.message = rng.choice(_WILD_MESSAGES)
    else:
        # Clean or partial: tier-based accuracy.
        accuracy: float = FIRE_ACCURACY[tier]
        if rng.random() > accuracy:
            impact = _apply_drift(rng, impact, 1)
        if outcome == CastOutcome.PARTIAL:
            result.message = rng.choice(_PARTIAL_MESSAGES)
        else:
            result.message = rng.choice(_CLEAN_MESSAGES)

    # Clamp impact to bounds.
    impact = Coordinate(
        max(0, min(BOARD_ROWS - 1, impact.r)),
        max(0, min(BOARD_COLUMNS - 1, impact.c)),
    )
    result.target_pos = (impact.r, impact.c)

    # -- Determine blast radius. --
    if chosen_radius >= 0:
        radius: int = RADIUS_CELLS[chosen_radius]
    else:
        # No choice — novice and apprentice are stuck with large.
        radius = RADIUS_CELLS[RADIUS_LARGE]

    # Wild outcome forces maximum radius regardless of choice.
    if outcome == CastOutcome.WILD:
        radius = RADIUS_CELLS[RADIUS_LARGE]

    # -- Base damage, reduced for partial. --
    base_dmg: int = FIRE_BASE_DAMAGE[tier]
    if outcome == CastOutcome.PARTIAL:
        base_dmg = max(1, base_dmg * 2 // 3)

    # -- Apply fire and damage in the blast zone. --
    total_dealt: int = 0
    kills: list[str] = []
    hit_monsters: list[str] = []

    for mr in range(impact.r - radius, impact.r + radius + 1):
        for mc in range(impact.c - radius, impact.c + radius + 1):
            if not (0 <= mr < BOARD_ROWS and 0 <= mc < BOARD_COLUMNS):
                continue
            # Manhattan distance from blast center.
            dist_from_center: int = abs(mr - impact.r) + abs(mc - impact.c)
            if dist_from_center > radius:
                continue

            # Damage falls off with distance squared.
            cell_dmg: int = max(1, base_dmg // (1 + dist_from_center * dist_from_center))

            pos: Coordinate = Coordinate(mr, mc)

            # Walls block the blast from spreading through them.
            if not board.line_of_sight(impact, pos):
                continue

            # Place fire on the board.
            board.add_fire(pos)

            monster = board.get_monster_at(pos)
            if monster is not None:
                actual: int = monster.take_damage(cell_dmg)
                total_dealt += actual
                brain = monster.species.get_brain()
                if not monster.is_alive:
                    if monster.last_action is not None:
                        brain.record_outcome(
                            monster, monster.last_action, REWARD_DEATH, engine
                        )
                    board.remove_monster(pos)
                    kills.append(monster.name)
                else:
                    hit_monsters.append(monster.name)
                    if monster.last_action is not None:
                        brain.record_outcome(
                            monster, monster.last_action,
                            REWARD_FIRE_DAMAGE, engine
                        )

            # Self-damage if player is in the blast zone.
            if pos == player_pos and outcome in (CastOutcome.WILD,
                                                  CastOutcome.MISFIRE):
                self_dmg: int = max(1, cell_dmg // 2)
                result.damage_taken += self_dmg

    result.damage_dealt = total_dealt

    # -- Fear reward for monsters near the blast but not hit. --
    fear_radius: int = radius + 2
    for mr in range(impact.r - fear_radius, impact.r + fear_radius + 1):
        for mc in range(impact.c - fear_radius, impact.c + fear_radius + 1):
            if not (0 <= mr < BOARD_ROWS and 0 <= mc < BOARD_COLUMNS):
                continue
            dist_fc: int = abs(mr - impact.r) + abs(mc - impact.c)
            if dist_fc <= radius or dist_fc > fear_radius:
                continue
            pos = Coordinate(mr, mc)
            monster = board.get_monster_at(pos)
            if monster is not None and monster.is_alive:
                brain = monster.species.get_brain()
                if monster.last_action is not None:
                    brain.record_outcome(
                        monster, monster.last_action,
                        REWARD_FIRE_NEAR, engine
                    )

    # -- Append kill/hit info to the message. --
    if kills:
        kill_str: str = ", ".join(kills)
        result.message += f" The flames consume the {kill_str}!"
    elif hit_monsters:
        hit_str: str = ", ".join(hit_monsters)
        result.message += f" Fire scorches the {hit_str}."

    return result
