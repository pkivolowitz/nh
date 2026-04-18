# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""Tests for the six-sense perception model."""

from __future__ import annotations

import pytest

from game.senses import (
    Senses, HUMAN_SENSES,
    BASE_SIGHT_LIT, BASE_SIGHT_DARK, BASE_SMELL, BASE_TOUCH, BASE_ESP,
)


class TestHumanBaseline:
    """Humans are the unit of measurement — every factor must be 1.0."""

    def test_human_all_ones(self):
        assert HUMAN_SENSES.sight_lit == 1.0
        assert HUMAN_SENSES.sight_dark == 1.0
        assert HUMAN_SENSES.hearing == 1.0
        assert HUMAN_SENSES.smell == 1.0
        assert HUMAN_SENSES.touch == 1.0
        assert HUMAN_SENSES.esp == 1.0

    def test_default_constructor_is_human(self):
        """A bare Senses() must equal HUMAN_SENSES."""
        s = Senses()
        assert s == HUMAN_SENSES

    def test_human_sight_radius_matches_base(self):
        assert HUMAN_SENSES.sight_radius(target_lit=True) == BASE_SIGHT_LIT
        assert HUMAN_SENSES.sight_radius(target_lit=False) == BASE_SIGHT_DARK

    def test_human_smell_matches_base(self):
        assert HUMAN_SENSES.smell_radius() == BASE_SMELL

    def test_human_touch_matches_base(self):
        assert HUMAN_SENSES.touch_radius() == BASE_TOUCH

    def test_human_esp_matches_base(self):
        assert HUMAN_SENSES.esp_radius() == BASE_ESP

    def test_human_hearing_unit_scale(self):
        assert HUMAN_SENSES.hearing_threshold_scale() == 1.0


class TestFactorScaling:
    """Factors multiply the base units linearly."""

    def test_double_sight(self):
        s = Senses(sight_lit=2.0, sight_dark=2.0)
        assert s.sight_radius(target_lit=True) == 2.0 * BASE_SIGHT_LIT
        assert s.sight_radius(target_lit=False) == 2.0 * BASE_SIGHT_DARK

    def test_quarter_smell(self):
        s = Senses(smell=0.25)
        assert s.smell_radius() == 0.25 * BASE_SMELL

    def test_zero_factor_means_absent(self):
        """A factor of 0.0 zeroes the radius regardless of base."""
        s = Senses(esp=0.0)
        assert s.esp_radius() == 0.0

    def test_hearing_scale_inverse_to_factor(self):
        """Sharper hearing (higher factor) means smaller threshold multiplier."""
        s = Senses(hearing=2.0)
        assert s.hearing_threshold_scale() == pytest.approx(0.5)

    def test_hearing_factor_zero_is_infinite(self):
        """No hearing means no noise event can reach threshold."""
        s = Senses(hearing=0.0)
        assert s.hearing_threshold_scale() == float("inf")


class TestLightingSelection:
    """sight_radius(target_lit) must pick the correct lit/dark factor."""

    def test_lit_uses_lit_factor(self):
        s = Senses(sight_lit=3.0, sight_dark=0.1)
        assert s.sight_radius(target_lit=True) == 3.0 * BASE_SIGHT_LIT

    def test_dark_uses_dark_factor(self):
        s = Senses(sight_lit=0.1, sight_dark=3.0)
        assert s.sight_radius(target_lit=False) == 3.0 * BASE_SIGHT_DARK

    def test_lit_and_dark_are_independent(self):
        """Changing one factor must not affect the other computation."""
        s = Senses(sight_lit=10.0, sight_dark=0.5)
        lit = s.sight_radius(target_lit=True)
        dark = s.sight_radius(target_lit=False)
        assert lit != dark
        assert lit == 10.0 * BASE_SIGHT_LIT
        assert dark == 0.5 * BASE_SIGHT_DARK


class TestSpeciesConfigurations:
    """Spot-check the wired species sense profiles."""

    def test_jackal_excels_in_dark(self):
        from game.monster import get_species_registry
        jackal = get_species_registry()["jackal"].senses
        # Jackal dark vision must exceed human dark vision.
        assert jackal.sight_radius(False) > HUMAN_SENSES.sight_radius(False)
        # And jackal smell must be significantly stronger.
        assert jackal.smell_radius() > HUMAN_SENSES.smell_radius() * 3

    def test_rat_sees_poorly_in_light(self):
        from game.monster import get_species_registry
        rat = get_species_registry()["rat"].senses
        assert rat.sight_radius(True) < HUMAN_SENSES.sight_radius(True)

    def test_rat_has_the_best_nose(self):
        from game.monster import get_species_registry
        reg = get_species_registry()
        assert reg["rat"].senses.smell_radius() > reg["jackal"].senses.smell_radius()
