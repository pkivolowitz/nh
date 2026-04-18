# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""Regression tests for the fire-burns-items bug (fixed 2026-04-17)."""

from __future__ import annotations

from game.coordinate import Coordinate
from game.items import BaseItem, ItemType, Spellbook, Food
from game.magic import MagicSchool


def _find_floor_cell(board) -> Coordinate:
    """Return a coordinate of a navigable room cell for item placement."""
    from game.cell import CellBaseType
    for r in range(len(board.cells)):
        for c in range(len(board.cells[r])):
            if board.cells[r][c].base_type == CellBaseType.ROOM:
                return Coordinate(r, c)
    raise RuntimeError("no room cells on board")


class TestFireConsumesFlammables:
    """Fire must remove spellbooks, scrolls, and food from the cell."""

    def test_spellbook_burned(self, fresh_engine):
        pos = _find_floor_cell(fresh_engine.board)
        book = Spellbook(MagicSchool.FIRE)
        fresh_engine.board.add_goodie(pos, book)
        burned = fresh_engine.board.add_fire(pos)
        assert len(burned) == 1
        assert pos not in fresh_engine.board.goodies

    def test_food_burned(self, fresh_engine):
        pos = _find_floor_cell(fresh_engine.board)
        food = Food(name="crumb of bread", weight=1)
        fresh_engine.board.add_goodie(pos, food)
        burned = fresh_engine.board.add_fire(pos)
        assert len(burned) == 1
        assert "bread" in burned[0]
        assert pos not in fresh_engine.board.goodies

    def test_burned_items_named(self, fresh_engine):
        pos = _find_floor_cell(fresh_engine.board)
        fresh_engine.board.add_goodie(pos, Spellbook(MagicSchool.FIRE))
        burned = fresh_engine.board.add_fire(pos)
        assert any("spellbook" in name.lower() for name in burned)

    def test_no_items_returns_empty(self, fresh_engine):
        pos = _find_floor_cell(fresh_engine.board)
        burned = fresh_engine.board.add_fire(pos)
        assert burned == []


class TestFirePreservesPotions:
    """Glass potions survive fire — they don't shatter (yet)."""

    def test_potion_survives(self, fresh_engine):
        pos = _find_floor_cell(fresh_engine.board)
        potion = BaseItem()
        potion.type = ItemType.POTION
        potion.symbol = ord("!")
        potion.item_name = "potion of healing"
        potion.weight_per_item = 1
        potion.number_of_like_items = 1
        fresh_engine.board.add_goodie(pos, potion)
        burned = fresh_engine.board.add_fire(pos)
        assert burned == []
        # Potion must still be on the cell.
        assert pos in fresh_engine.board.goodies
        assert len(fresh_engine.board.goodies[pos]) == 1


class TestFireMixedPile:
    """A pile with both flammable and fireproof items partitions correctly."""

    def test_mixed_pile_burns_only_flammables(self, fresh_engine):
        pos = _find_floor_cell(fresh_engine.board)
        # Fireproof: potion.
        potion = BaseItem()
        potion.type = ItemType.POTION
        potion.symbol = ord("!")
        potion.item_name = "potion"
        potion.weight_per_item = 1
        potion.number_of_like_items = 1
        # Flammable: spellbook, food.
        book = Spellbook(MagicSchool.FIRE)
        food = Food()
        fresh_engine.board.add_goodie(pos, potion)
        fresh_engine.board.add_goodie(pos, book)
        fresh_engine.board.add_goodie(pos, food)
        burned = fresh_engine.board.add_fire(pos)
        assert len(burned) == 2
        # Only the potion remains.
        survivors = fresh_engine.board.goodies[pos]
        assert len(survivors) == 1
        assert survivors[0].type == ItemType.POTION
