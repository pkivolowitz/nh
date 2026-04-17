# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""Player state: traits, inventory, and status-line formatting.

Player inherits from Creature for a unified entity model.  The traits
array is kept in sync with Creature.hp / Creature.max_hp so existing
status-line formatting and ML state export continue to work.
"""

from __future__ import annotations

__version__ = "0.1.0"

import random
from enum import IntEnum, auto
from typing import Optional

from game.creature import Creature
from game.coordinate import Coordinate
from game.items import BaseItem, MAX_INVENTORY_SLOTS, letter_to_index, index_to_letter
from game.colors import CLR_PLAYER
from game.constants import PLAYER_SPEED
from game.magic import SpellKnowledge


class Trait(IntEnum):
    """Indices into the traits arrays."""
    STRENGTH = 0
    INTELLIGENCE = auto()
    CONSTITUTION = auto()
    DEXTERITY = auto()
    LEVEL = auto()
    EXPERIENCE = auto()
    HEALTH = auto()
    CONCENTRATION = auto()
    TRAIT_COUNT = auto()


class Player(Creature):
    """The player character, with stats, position, and inventory."""

    def __init__(self, rng: random.Random) -> None:
        tc = int(Trait.TRAIT_COUNT)
        current_traits: list[int] = [0] * tc
        maximum_traits: list[int] = [0] * tc

        # Roll stat-based traits.
        for t in (Trait.STRENGTH, Trait.INTELLIGENCE, Trait.CONSTITUTION,
                  Trait.DEXTERITY, Trait.HEALTH, Trait.CONCENTRATION):
            v = rng.randint(12, 18)
            current_traits[t] = maximum_traits[t] = v

        # Fixed starting values.
        current_traits[Trait.LEVEL] = maximum_traits[Trait.LEVEL] = 1
        current_traits[Trait.EXPERIENCE] = maximum_traits[Trait.EXPERIENCE] = 0

        super().__init__(
            name="Unknown Player",
            pos=Coordinate(),
            speed=PLAYER_SPEED,
            max_hp=current_traits[Trait.HEALTH],
            symbol=ord("@"),
            color_pair=CLR_PLAYER,
        )

        self.current_traits: list[int] = current_traits
        self.maximum_traits: list[int] = maximum_traits

        # Inventory: 52 slots (a-z, A-Z).
        self.inventory: list[Optional[BaseItem]] = [None] * MAX_INVENTORY_SLOTS

        self.role: str = "Caveman"
        self.race: str = "Human"
        self.alignment: str = "Neutral"

        # Magic system.
        self.magic: SpellKnowledge = SpellKnowledge()

    # -- damage / healing (keep traits in sync) ----------------------------

    def take_damage(self, amount: int) -> int:
        """Apply damage and keep the traits array in sync."""
        actual: int = super().take_damage(amount)
        self.current_traits[Trait.HEALTH] = self.hp
        return actual

    def heal(self, amount: int) -> int:
        """Restore HP and keep the traits array in sync."""
        actual: int = super().heal(amount)
        self.current_traits[Trait.HEALTH] = self.hp
        return actual

    def spend_concentration(self, amount: int) -> bool:
        """Spend *amount* concentration.  Returns False if insufficient."""
        current: int = self.current_traits[Trait.CONCENTRATION]
        if current < amount:
            return False
        self.current_traits[Trait.CONCENTRATION] = current - amount
        return True

    def restore_concentration(self, amount: int) -> int:
        """Restore up to *amount* concentration.  Returns actual restored."""
        current: int = self.current_traits[Trait.CONCENTRATION]
        maximum: int = self.maximum_traits[Trait.CONCENTRATION]
        room: int = maximum - current
        actual: int = min(amount, room)
        self.current_traits[Trait.CONCENTRATION] = current + actual
        return actual

    # -- inventory management ------------------------------------------

    def next_available_letter(self) -> str:
        """First empty inventory slot as a letter, or '' if full."""
        for i in range(MAX_INVENTORY_SLOTS):
            if self.inventory[i] is None:
                return index_to_letter(i)
        return ""

    def add_to_inventory(self, item: BaseItem) -> str:
        """Add *item* to inventory, stacking with a matching item first.

        Returns the assigned letter (existing or new slot), or '' if full.
        """
        # Try to stack with an existing item.
        for i, existing in enumerate(self.inventory):
            if existing is not None and existing.can_stack_with(item):
                existing.number_of_like_items += item.number_of_like_items
                return index_to_letter(i)
        # No stack match — use a new slot.
        letter = self.next_available_letter()
        if not letter:
            return ""
        idx = letter_to_index(letter)
        self.inventory[idx] = item
        return letter

    def remove_from_inventory(self, letter: str) -> Optional[BaseItem]:
        """Remove and return the item in slot *letter*, or None."""
        idx = letter_to_index(letter)
        if idx < 0 or idx >= MAX_INVENTORY_SLOTS:
            return None
        item = self.inventory[idx]
        self.inventory[idx] = None
        return item

    def weight_of_inventory(self) -> int:
        """Total weight of every carried item."""
        return sum(it.weight() for it in self.inventory if it is not None)

    def max_carry_weight(self) -> int:
        """Maximum carry weight based on STRENGTH.

        Base 50 + 10 per STR point above 10.  STR 12 = 70, STR 18 = 130.
        """
        return 50 + self.current_traits[Trait.STRENGTH] * 10 - 100

    def is_overburdened(self) -> bool:
        """True if carrying more than max carry weight."""
        return self.weight_of_inventory() > self.max_carry_weight()

    def melee_damage_bonus(self) -> int:
        """Bonus melee damage from STRENGTH.

        STR 14 = +0, STR 18 = +2, STR 12 = -1.
        Minimum bonus is -1 so weak characters aren't completely useless.
        """
        return max(-1, (self.current_traits[Trait.STRENGTH] - 14) // 2)

    def kick_bonus(self) -> int:
        """Bonus kick chance percentage from STRENGTH.

        STR 14 = +0%, STR 18 = +20%.  Applied to locked/closed door
        kick success rolls.
        """
        return max(0, (self.current_traits[Trait.STRENGTH] - 14) * 5)

    def total_inventory_count(self) -> int:
        """Sum of item counts across all occupied slots."""
        return sum(it.number_of_like_items for it in self.inventory if it is not None)

    def inventory_count(self) -> int:
        """Number of occupied inventory slots."""
        return sum(1 for it in self.inventory if it is not None)

    # -- ML state ------------------------------------------------------

    def get_state(self) -> dict:
        """Machine-readable snapshot for the agent interface."""
        state: dict = super().get_state()
        state["traits"] = {t.name: self.current_traits[t] for t in Trait
                           if t != Trait.TRAIT_COUNT}
        state["inventory_count"] = self.inventory_count()
        state["inventory_weight"] = self.weight_of_inventory()
        return state
