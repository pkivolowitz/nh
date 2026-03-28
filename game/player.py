# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""Player state: traits, inventory, and status-line formatting."""

from __future__ import annotations

__version__ = "0.1.0"

import random
from enum import IntEnum, auto
from typing import Optional

from game.coordinate import Coordinate
from game.items import BaseItem, MAX_INVENTORY_SLOTS, letter_to_index, index_to_letter


class Trait(IntEnum):
    """Indices into the traits arrays."""
    INTELLIGENCE = 0
    CONSTITUTION = auto()
    DEXTERITY = auto()
    LEVEL = auto()
    EXPERIENCE = auto()
    HEALTH = auto()
    CONCENTRATION = auto()
    TRAIT_COUNT = auto()


class Player:
    """The player character, with stats, position, and inventory."""

    def __init__(self, rng: random.Random) -> None:
        tc = int(Trait.TRAIT_COUNT)
        self.current_traits: list[int] = [0] * tc
        self.maximum_traits: list[int] = [0] * tc

        # Roll stat-based traits.
        for t in (Trait.INTELLIGENCE, Trait.CONSTITUTION, Trait.DEXTERITY,
                  Trait.HEALTH, Trait.CONCENTRATION):
            v = rng.randint(12, 18)
            self.current_traits[t] = self.maximum_traits[t] = v

        # Fixed starting values.
        self.current_traits[Trait.LEVEL] = self.maximum_traits[Trait.LEVEL] = 1
        self.current_traits[Trait.EXPERIENCE] = self.maximum_traits[Trait.EXPERIENCE] = 0

        # Inventory: 52 slots (a-z, A-Z).
        self.inventory: list[Optional[BaseItem]] = [None] * MAX_INVENTORY_SLOTS

        self.name: str = "Unknown Player"
        self.role: str = "Caveman"
        self.race: str = "Human"
        self.alignment: str = "Neutral"

        self.pos: Coordinate = Coordinate()

    # -- inventory management ------------------------------------------

    def next_available_letter(self) -> str:
        """First empty inventory slot as a letter, or '' if full."""
        for i in range(MAX_INVENTORY_SLOTS):
            if self.inventory[i] is None:
                return index_to_letter(i)
        return ""

    def add_to_inventory(self, item: BaseItem) -> str:
        """Add *item* to the next free slot.

        Returns the assigned letter, or '' if full.
        """
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

    def total_inventory_count(self) -> int:
        """Sum of item counts across all occupied slots."""
        return sum(it.number_of_like_items for it in self.inventory if it is not None)

    def inventory_count(self) -> int:
        """Number of occupied inventory slots."""
        return sum(1 for it in self.inventory if it is not None)

    # -- status lines --------------------------------------------------

    @staticmethod
    def _fmt_stat(label: str, cur: int, mx: int, w: int) -> str:
        """Format a stat as ``LABEL:CUR/MAX`` with right-justified numbers."""
        return f"{label}:{cur:>{w}}/{mx:>{w}}"

    def status_line_upper(self) -> str:
        """Name, role, and volatile stats."""
        title = f"{self.name} the {self.role}"
        parts = [
            f"{title:<20s}",
            self._fmt_stat("HLTH", self.current_traits[Trait.HEALTH],
                           self.maximum_traits[Trait.HEALTH], 3),
            self._fmt_stat("CNC", self.current_traits[Trait.CONCENTRATION],
                           self.maximum_traits[Trait.CONCENTRATION], 3),
            self._fmt_stat("LVL", self.current_traits[Trait.LEVEL],
                           self.maximum_traits[Trait.LEVEL], 2),
            self._fmt_stat("EXP", self.current_traits[Trait.EXPERIENCE],
                           self.maximum_traits[Trait.EXPERIENCE], 6),
        ]
        return "  ".join(parts)

    def status_line_lower(self) -> str:
        """Race, alignment, and stat blocks."""
        desc = f"{self.race} {self.alignment}"
        parts = [
            f"{desc:<20s}",
            self._fmt_stat("INT", self.current_traits[Trait.INTELLIGENCE],
                           self.maximum_traits[Trait.INTELLIGENCE], 3),
            self._fmt_stat("CON", self.current_traits[Trait.CONSTITUTION],
                           self.maximum_traits[Trait.CONSTITUTION], 3),
            self._fmt_stat("DEX", self.current_traits[Trait.DEXTERITY],
                           self.maximum_traits[Trait.DEXTERITY], 3),
            f"Items:{self.inventory_count():2d}/{MAX_INVENTORY_SLOTS}",
            f"Wt:{self.weight_of_inventory()}",
        ]
        return "  ".join(parts)

    # -- ML state ------------------------------------------------------

    def get_state(self) -> dict:
        """Machine-readable snapshot for the agent interface."""
        return {
            "pos": self.pos.to_tuple(),
            "traits": {t.name: self.current_traits[t] for t in Trait
                       if t != Trait.TRAIT_COUNT},
            "inventory_count": self.inventory_count(),
            "inventory_weight": self.weight_of_inventory(),
        }
