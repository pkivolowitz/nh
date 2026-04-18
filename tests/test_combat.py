# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""Tests for the combat math primitives."""

from __future__ import annotations

import random

from game.combat import BumpAttack, CombatResult
from game.creature import Creature
from game.coordinate import Coordinate


def _dummy(hp: int = 10) -> Creature:
    return Creature(
        name="dummy", pos=Coordinate(0, 0), speed=10,
        max_hp=hp, symbol=ord("?"), color_pair=0,
    )


class TestBumpAttackDamageBounds:
    """Damage rolls must stay within [dice, dice * sides]."""

    def test_damage_at_least_dice(self):
        attacker = _dummy()
        defender = _dummy(hp=1000)
        attack = BumpAttack(dice=3, sides=4)
        rng = random.Random(0)
        for _ in range(100):
            before = defender.hp
            attack.execute(attacker, defender, rng)
            dealt = before - defender.hp
            assert dealt >= 3, f"dealt {dealt} < minimum 3 (3d4)"

    def test_damage_at_most_dice_times_sides(self):
        attacker = _dummy()
        defender = _dummy(hp=1000)
        attack = BumpAttack(dice=2, sides=6)
        rng = random.Random(0)
        for _ in range(100):
            before = defender.hp
            attack.execute(attacker, defender, rng)
            dealt = before - defender.hp
            assert dealt <= 12, f"dealt {dealt} > maximum 12 (2d6)"


class TestBumpAttackKillDetection:
    """defender_killed must reflect the defender's actual alive state."""

    def test_kill_flag_true_when_defender_dies(self):
        attacker = _dummy()
        defender = _dummy(hp=1)
        attack = BumpAttack(dice=5, sides=10)
        rng = random.Random(0)
        result = attack.execute(attacker, defender, rng)
        assert result.defender_killed
        assert not defender.is_alive

    def test_kill_flag_false_when_defender_survives(self):
        attacker = _dummy()
        defender = _dummy(hp=1000)
        attack = BumpAttack(dice=1, sides=2)
        rng = random.Random(0)
        result = attack.execute(attacker, defender, rng)
        assert not result.defender_killed
        assert defender.is_alive


class TestDamageBonus:
    """The damage_bonus parameter must add to the rolled damage."""

    def test_positive_bonus_increases_damage(self):
        attacker = _dummy()
        defender = _dummy(hp=1000)
        attack = BumpAttack(dice=1, sides=1)  # Always rolls 1.
        rng = random.Random(0)
        before = defender.hp
        result = attack.execute(attacker, defender, rng, damage_bonus=5)
        assert result.damage == 6  # 1 + 5
        assert defender.hp == before - 6

    def test_negative_bonus_clamped_to_zero(self):
        attacker = _dummy()
        defender = _dummy(hp=1000)
        attack = BumpAttack(dice=1, sides=1)
        rng = random.Random(0)
        before = defender.hp
        result = attack.execute(attacker, defender, rng, damage_bonus=-100)
        assert result.damage == 0
        assert defender.hp == before


class TestDescribeString:
    """describe() returns the conventional dice-notation representation."""

    def test_describe_format(self):
        attack = BumpAttack(dice=2, sides=6, verb="claws")
        assert attack.describe() == "claws (2d6)"
