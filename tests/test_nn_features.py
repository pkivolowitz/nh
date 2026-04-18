# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""Tests for the NN feature extractors and legal-action masking."""

from __future__ import annotations

import numpy as np
import pytest

from game.nn_features import (
    JackalFeatures, RatFeatures,
    FeatureExtractor, get_extractor,
    ACTION_ORDER, NUM_ACTIONS,
)


class TestFeatureDimensions:
    def test_jackal_dim_is_fixed(self):
        ext = JackalFeatures()
        assert ext.feature_dim == 21

    def test_rat_dim_is_fixed(self):
        ext = RatFeatures()
        assert ext.feature_dim == 19


class TestFeatureValues:
    """Extracted vectors must match the documented layout."""

    def test_jackal_one_hots_are_exclusive(self, fresh_engine):
        """Each one-hot block must sum to exactly 1.0."""
        from game.monster import get_species_registry
        from game.coordinate import Coordinate
        import random as _r

        spec = get_species_registry()["jackal"]
        m = _r.Random(1)
        from game.monster import Monster
        jackal = Monster(spec, Coordinate(5, 5), m)

        perception = {
            "can_see_prey": True,
            "prey_distance": "close",
            "hp": "healthy",
            "pack": "pair",
            "hear": "faint",
            "noise_dir": (1, 0),
            "smell": True,
            "scent_dir": (-1, 1),
        }
        vec = JackalFeatures().extract(jackal, perception, fresh_engine)
        assert vec.dtype == np.float32
        # Layout: [0] see, [1:5] dist (4), [5:8] hp (3), [8:11] pack (3),
        # [11:14] hear (3), [14:16] ndir (2), [16] smell,
        # [17:19] scent (2), [19] hp_ratio, [20] dist_norm
        assert vec[0] == 1.0  # can_see
        assert vec[1:5].sum() == 1.0  # distance one-hot
        assert vec[5:8].sum() == 1.0  # hp one-hot
        assert vec[8:11].sum() == 1.0  # pack one-hot
        assert vec[11:14].sum() == 1.0  # hear one-hot
        # Smell detected, scent dir set.
        assert vec[16] == 1.0
        assert vec[17:19].tolist() == [-1.0, 1.0]

    def test_rat_food_direction_carries(self, fresh_engine):
        from game.monster import get_species_registry, Monster
        from game.coordinate import Coordinate
        import random as _r

        spec = get_species_registry()["rat"]
        rat = Monster(spec, Coordinate(3, 3), _r.Random(2))
        perception = {
            "can_see_prey": False,
            "prey_distance": "far",
            "hp": "critical",
            "food_nearby": True,
            "food_dir": (1, -1),
            "escape": "few",
            "smell_predator": True,
            "scent_dir": (0, 1),
        }
        vec = RatFeatures().extract(rat, perception, fresh_engine)
        # food_nearby at index 8, food_dir at 9:11
        assert vec[8] == 1.0
        assert vec[9:11].tolist() == [1.0, -1.0]
        # smell_predator at 14, scent_dir at 15:17
        assert vec[14] == 1.0
        assert vec[15:17].tolist() == [0.0, 1.0]


class TestRegistry:
    def test_get_extractor_known_species(self):
        assert isinstance(get_extractor("jackal"), JackalFeatures)
        assert isinstance(get_extractor("rat"), RatFeatures)

    def test_get_extractor_unknown_raises(self):
        with pytest.raises(KeyError):
            get_extractor("dragon")


class TestLegalActionMask:
    """WAIT is always legal; movement masked by real board navigability."""

    def test_wait_always_legal(self, fresh_engine):
        for m in fresh_engine.board.get_all_monsters():
            mask = FeatureExtractor.legal_action_mask(m, fresh_engine)
            assert mask[0] == True, "WAIT must always be legal"
            break
        else:
            pytest.skip("no monsters spawned at this seed")

    def test_mask_has_at_least_one_true(self, fresh_engine):
        """Every in-play monster has at least WAIT available."""
        for m in fresh_engine.board.get_all_monsters():
            mask = FeatureExtractor.legal_action_mask(m, fresh_engine)
            assert mask.any()

    def test_mask_length_matches_action_space(self, fresh_engine):
        for m in fresh_engine.board.get_all_monsters():
            mask = FeatureExtractor.legal_action_mask(m, fresh_engine)
            assert mask.shape == (NUM_ACTIONS,)
            assert mask.dtype == np.bool_
            break
        else:
            pytest.skip("no monsters")


class TestActionOrder:
    def test_order_matches_action_enum(self):
        from game.actions import Action
        assert ACTION_ORDER[0] == Action.WAIT
        # Next 8 are the movements in enum order.
        assert len(ACTION_ORDER) == 9
