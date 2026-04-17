# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""Item types, base item, and concrete item classes."""

from __future__ import annotations

__version__ = "0.1.0"

from enum import IntEnum, auto
from typing import Optional

from game.constants import MAX_INVENTORY_SLOTS
from game.magic import MagicSchool, SCHOOL_NAMES


class ItemType(IntEnum):
    """Discriminant for polymorphic item serialization."""
    BASE_ITEM = 0
    POTION = auto()
    SCROLL = auto()
    SPELLBOOK = auto()
    FOOD = auto()


def letter_to_index(c: str) -> int:
    """Convert an inventory letter to a slot index.

    a-z → 0-25, A-Z → 26-51, anything else → -1.
    """
    if "a" <= c <= "z":
        return ord(c) - ord("a")
    if "A" <= c <= "Z":
        return ord(c) - ord("A") + 26
    return -1


def index_to_letter(i: int) -> str:
    """Convert a slot index to an inventory letter.

    0-25 → a-z, 26-51 → A-Z, out of range → '?'.
    """
    if 0 <= i < 26:
        return chr(ord("a") + i)
    if 26 <= i < 52:
        return chr(ord("A") + (i - 26))
    return "?"


class BaseItem:
    """Generic inventory/floor item.

    Subclasses override ``can_stack_with`` for stackable types.
    """

    __slots__ = ("type", "weight_per_item", "number_of_like_items",
                 "symbol", "item_name")

    def __init__(self) -> None:
        self.type: ItemType = ItemType.BASE_ITEM
        self.weight_per_item: int = 0
        self.number_of_like_items: int = 1
        self.symbol: int = ord("?")
        self.item_name: str = "Unknown Item"

    def weight(self) -> int:
        """Total carried weight of this item stack."""
        return self.weight_per_item * self.number_of_like_items

    def describe(self) -> str:
        """Human-readable description including stack count."""
        if self.number_of_like_items > 1:
            return f"{self.number_of_like_items} {self.item_name}s"
        return self.item_name

    def can_stack_with(self, other: BaseItem) -> bool:
        """Whether *other* can merge into this stack.  Default: no."""
        return False


class Spellbook(BaseItem):
    """A spellbook found on the dungeon floor.

    Each spellbook teaches one school.  The first book in a school
    unlocks the ability to cast it.  Subsequent books in the same
    school grant proficiency XP.  All spellbooks crumble to dust
    once read — they cannot be read again.
    """

    __slots__ = ("school",)

    def __init__(self, school: MagicSchool = MagicSchool.FIRE) -> None:
        super().__init__()
        self.type = ItemType.SPELLBOOK
        self.symbol = ord("+")
        self.weight_per_item = 5
        self.number_of_like_items = 1
        self.school: MagicSchool = school
        self.item_name = f"Spellbook of {SCHOOL_NAMES[school]}"

    def can_stack_with(self, other: BaseItem) -> bool:
        """Spellbooks never stack — each contains a different spell."""
        return False


# Food names and weights — small scraps that attract vermin.
FOOD_KINDS: list[tuple[str, int]] = [
    ("crumb of bread", 1),
    ("morsel of cheese", 1),
    ("dried meat scrap", 2),
    ("stale biscuit", 2),
]


class Food(BaseItem):
    """A small edible item found on the dungeon floor.

    Food attracts rats and other scavengers.  The player can pick
    it up and drop it as bait.
    """

    __slots__ = ("food_name",)

    def __init__(self, name: str = "crumb of bread",
                 weight: int = 1) -> None:
        super().__init__()
        self.type = ItemType.FOOD
        self.symbol = ord("%")
        self.weight_per_item = weight
        self.number_of_like_items = 1
        self.food_name: str = name
        self.item_name = name

    def can_stack_with(self, other: BaseItem) -> bool:
        """Food of the same kind stacks."""
        return (isinstance(other, Food)
                and other.food_name == self.food_name)
