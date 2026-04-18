# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""Monster types, species definitions, and the species registry.

Each monster species is defined once as a ``MonsterSpecies`` template.
Individual ``Monster`` instances are spawned from the template with
rolled HP and a reference to the shared species brain.

The species registry is the single authoritative catalog of all monster
types in the game.  Add new species here.
"""

from __future__ import annotations

__version__ = "0.1.0"

import random
from typing import Optional, TYPE_CHECKING

from game.creature import Creature
from game.coordinate import Coordinate
from game.combat import CombatAction, BumpAttack
from game.colors import CLR_BROWN
from game.actions import Action
from game.constants import NOISE_MONSTER_MOVE
from game.senses import Senses

if TYPE_CHECKING:
    from game.brain import Brain


class MonsterSpecies:
    """Immutable template defining a type of monster.

    All instances share stats, attacks, and brain.  Individual
    variation comes from HP rolls and learned behavior.
    """

    def __init__(self, name: str, symbol: int, color_pair: int,
                 speed: int, hp_dice: int, hp_sides: int,
                 ac: int, base_level: int,
                 attacks: list[CombatAction],
                 flags: set[str],
                 spawn_group_min: int, spawn_group_max: int,
                 min_depth: int, max_depth: int,
                 frequency: int,
                 brain_class: type,
                 move_noise: int = NOISE_MONSTER_MOVE,
                 noise_description: str = "sound of movement",
                 senses: Optional[Senses] = None) -> None:
        self.name: str = name
        self.symbol: int = symbol
        self.color_pair: int = color_pair
        self.speed: int = speed
        self.hp_dice: int = hp_dice
        self.hp_sides: int = hp_sides
        self.ac: int = ac
        self.base_level: int = base_level
        self.attacks: list[CombatAction] = attacks
        self.flags: set[str] = flags
        self.spawn_group_min: int = spawn_group_min
        self.spawn_group_max: int = spawn_group_max
        self.min_depth: int = min_depth
        self.max_depth: int = max_depth
        self.frequency: int = frequency
        self.move_noise: int = move_noise
        self.noise_description: str = noise_description
        # Perceptual profile — all six senses scaled against humans.
        self.senses: Senses = senses if senses is not None else Senses()
        self._brain_class: type = brain_class
        self._brain: Optional[Brain] = None

    def roll_hp(self, rng: random.Random) -> int:
        """Roll hit points for a new individual."""
        return sum(rng.randint(1, self.hp_sides) for _ in range(self.hp_dice))

    def get_brain(self) -> Brain:
        """Get the shared persistent brain for this species.

        Lazy-loaded from the BrainRegistry on first access.
        """
        if self._brain is None:
            from game.brain import BrainRegistry
            self._brain = BrainRegistry.get(self.name, self._brain_class)
        return self._brain


class Monster(Creature):
    """A single monster instance on the board."""

    def __init__(self, species: MonsterSpecies, pos: Coordinate,
                 rng: random.Random) -> None:
        hp: int = species.roll_hp(rng)
        super().__init__(
            name=species.name,
            pos=pos,
            speed=species.speed,
            max_hp=hp,
            symbol=species.symbol,
            color_pair=species.color_pair,
        )
        self.species: MonsterSpecies = species
        self.ac: int = species.ac
        self.base_level: int = species.base_level
        # Adopt the species' perceptual profile.
        self.senses = species.senses

        # Brain learning state -- tracks what this individual just did
        # so rewards are attributed to the correct (state, action) pair.
        self.last_action: Optional[Action] = None
        self.last_state_key: Optional[str] = None

    def get_state(self) -> dict:
        """ML observation including species information."""
        state: dict = super().get_state()
        state["species"] = self.species.name
        state["ac"] = self.ac
        return state


# ---------------------------------------------------------------------------
# Species registry
# ---------------------------------------------------------------------------

def _build_species_registry() -> dict[str, MonsterSpecies]:
    """Construct the master catalog of all monster species."""
    from game.brain import JackalBrain, RatBrain
    from game.colors import CLR_GRAY

    registry: dict[str, MonsterSpecies] = {}

    # Jackal -- the quintessential early-game pack mob.
    # Individually trivial (1-4 HP, 1-2 bite damage), dangerous in
    # groups of 2-4.  Matches NetHack: symbol 'd', brown, speed 12,
    # AC 7, level 0, depth 1-6.
    registry["jackal"] = MonsterSpecies(
        name="jackal",
        symbol=ord("d"),
        color_pair=CLR_BROWN,
        speed=12,
        hp_dice=1,
        hp_sides=4,
        ac=7,
        base_level=0,
        attacks=[BumpAttack(dice=1, sides=2, verb="bites")],
        flags={"hostile", "animal", "nohands", "carnivore", "pack"},
        spawn_group_min=2,
        spawn_group_max=4,
        min_depth=1,
        max_depth=6,
        frequency=3,
        brain_class=JackalBrain,
        move_noise=4,
        noise_description="soft padding of paws",
        # Jackal: strong night vision and keen nose, weak ESP (none).
        senses=Senses(
            sight_lit=1.0,
            sight_dark=4.0,
            hearing=2.0,
            smell=6.0,
            touch=1.0,
            esp=0.0,
        ),
    )

    # Rat -- cowardly scavenger.  Flees the player, seeks food on the
    # floor.  Only bites when cornered.  Individually weak (1-3 HP,
    # 1d3 bite), spawns solo or in pairs.  Symbol 'r', gray.
    registry["rat"] = MonsterSpecies(
        name="rat",
        symbol=ord("r"),
        color_pair=CLR_GRAY,
        speed=10,
        hp_dice=1,
        hp_sides=3,
        ac=9,
        base_level=0,
        attacks=[BumpAttack(dice=1, sides=3, verb="bites")],
        flags={"hostile", "animal", "nohands", "omnivore"},
        spawn_group_min=1,
        spawn_group_max=2,
        min_depth=1,
        max_depth=4,
        frequency=4,
        brain_class=RatBrain,
        move_noise=2,
        noise_description="faint scratching",
        # Rat: nearly blind, superb nose, whiskers extend touch.
        senses=Senses(
            sight_lit=0.5,
            sight_dark=1.0,
            hearing=1.5,
            smell=7.0,
            touch=2.0,
            esp=0.0,
        ),
    )

    return registry


# Lazy-initialized singleton.
_SPECIES_REGISTRY: Optional[dict[str, MonsterSpecies]] = None


def get_species_registry() -> dict[str, MonsterSpecies]:
    """Get the species registry, initializing on first call."""
    global _SPECIES_REGISTRY
    if _SPECIES_REGISTRY is None:
        _SPECIES_REGISTRY = _build_species_registry()
    return _SPECIES_REGISTRY


def get_eligible_species(dungeon_level: int) -> list[MonsterSpecies]:
    """Return species eligible to spawn at *dungeon_level*."""
    registry: dict[str, MonsterSpecies] = get_species_registry()
    return [
        s for s in registry.values()
        if s.min_depth <= dungeon_level <= s.max_depth
    ]
