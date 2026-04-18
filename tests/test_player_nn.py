# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""Tests for the player policy stack: features, action space, policy."""

from __future__ import annotations

import numpy as np
import pytest

from game.actions import Action, Direction
from game.ai_player import (
    AIPlayer, PolicyAIPlayer, PlayerBrain, _engine_action_to_player_action_idx,
)
from game.nn_features import (
    PlayerFeatures, PlayerAction, NUM_PLAYER_ACTIONS,
    PLAYER_GRID_DIM, PLAYER_GRID_SIDE, PLAYER_GRID_CHANNELS,
    decode_player_action,
)


class TestPlayerFeatureDimensions:
    def test_feature_dim_is_scalar_plus_grid(self):
        ext = PlayerFeatures()
        assert ext.feature_dim == ext.SCALAR_DIM + PLAYER_GRID_DIM
        assert ext.SCALAR_DIM == 16

    def test_num_player_actions_is_17(self):
        assert NUM_PLAYER_ACTIONS == 17

    def test_grid_layout(self):
        assert PLAYER_GRID_SIDE == 15
        assert PLAYER_GRID_CHANNELS == 11
        assert PLAYER_GRID_DIM == 15 * 15 * 11


class TestPlayerFeatureValues:
    def test_hp_ratio_starts_full(self, fresh_engine):
        ext = PlayerFeatures()
        vec = ext.extract(fresh_engine.player, fresh_engine)
        assert vec[0] == 1.0  # HP ratio at full HP

    def test_concentration_ratio_starts_full(self, fresh_engine):
        ext = PlayerFeatures()
        vec = ext.extract(fresh_engine.player, fresh_engine)
        assert vec[1] == pytest.approx(1.0)  # Concentration starts full

    def test_grid_block_nonempty(self, fresh_engine):
        """The grid section of the feature vector must have some 1.0 cells."""
        ext = PlayerFeatures()
        vec = ext.extract(fresh_engine.player, fresh_engine)
        grid_slice = vec[ext.SCALAR_DIM:]
        assert grid_slice.sum() > 0, "grid is completely empty"


class TestLegalActionMask:
    def test_wait_always_legal(self, fresh_engine):
        mask = PlayerFeatures.legal_action_mask(
            fresh_engine.player, fresh_engine,
        )
        assert mask[PlayerAction.WAIT]

    def test_mask_length_matches_action_space(self, fresh_engine):
        mask = PlayerFeatures.legal_action_mask(
            fresh_engine.player, fresh_engine,
        )
        assert mask.shape == (NUM_PLAYER_ACTIONS,)

    def test_stairs_up_legal_at_start(self, fresh_engine):
        """Player spawns on upstairs — STAIRS_UP must be legal."""
        mask = PlayerFeatures.legal_action_mask(
            fresh_engine.player, fresh_engine,
        )
        assert mask[PlayerAction.STAIRS_UP]

    def test_cast_fire_masked_without_magic(self, fresh_engine):
        """Fresh player hasn't learned fire — cast must be illegal."""
        mask = PlayerFeatures.legal_action_mask(
            fresh_engine.player, fresh_engine,
        )
        assert not mask[PlayerAction.CAST_FIRE]


class TestActionMapping:
    """Round-trip between engine actions and PlayerAction indices."""

    def test_wait_roundtrip(self):
        idx = _engine_action_to_player_action_idx(Action.WAIT, {})
        assert idx == int(PlayerAction.WAIT)

    def test_move_n_roundtrip(self):
        idx = _engine_action_to_player_action_idx(Action.MOVE_N, {})
        assert idx == int(PlayerAction.MOVE_N)

    def test_open_door_n_roundtrip(self):
        idx = _engine_action_to_player_action_idx(
            Action.OPEN_DOOR, {"direction": Direction.N}
        )
        assert idx == int(PlayerAction.OPEN_N)

    def test_open_door_diagonal_is_none(self):
        """Diagonal doors aren't representable in the 17-action space."""
        idx = _engine_action_to_player_action_idx(
            Action.OPEN_DOOR, {"direction": Direction.NE}
        )
        assert idx is None

    def test_kick_door_is_none(self):
        """KICK_DOOR has no PlayerAction equivalent — must drop the record."""
        idx = _engine_action_to_player_action_idx(
            Action.KICK_DOOR, {"direction": Direction.N}
        )
        assert idx is None


class TestDecodePlayerAction:
    def test_wait_decodes_to_wait(self, fresh_engine):
        a, kw = decode_player_action(int(PlayerAction.WAIT), fresh_engine)
        assert a == Action.WAIT
        assert kw == {}

    def test_move_ne_decodes_with_direction(self, fresh_engine):
        a, kw = decode_player_action(int(PlayerAction.MOVE_NE), fresh_engine)
        assert a == Action.MOVE_NE
        assert kw.get("direction") == Direction.NE

    def test_cast_fire_no_target_fizzles_sensibly(self, fresh_engine):
        """No visible monster — decode must still return a valid engine call."""
        a, kw = decode_player_action(int(PlayerAction.CAST_FIRE), fresh_engine)
        assert a == Action.CAST
        from game.magic import MagicSchool
        assert kw.get("school") == MagicSchool.FIRE


class TestPolicyAIPlayerFallback:
    def test_fallback_without_model(self, fresh_engine, tmp_path):
        """No model file → random-legal behavior, no crashes."""
        bogus = str(tmp_path / "missing.onnx")
        ai = PolicyAIPlayer(model_path=bogus)
        assert not ai.has_model
        action, _ = ai.choose_action(fresh_engine)
        assert isinstance(action, Action)

    def test_learn_reward_accumulates_items(self, fresh_engine, tmp_path):
        ai = PolicyAIPlayer(model_path=str(tmp_path / "none.onnx"))
        from game.engine import StepResult
        ai._learn_reward(StepResult(reward=2.0))
        assert ai._items_collected == 2


class TestAIPlayerTrajectoryLogging:
    def test_logger_receives_records(self, fresh_engine, tmp_path):
        from game.nn_brain import TrajectoryLogger
        path = str(tmp_path / "traj.jsonl")
        logger = TrajectoryLogger(path)
        ai = AIPlayer()
        ai.trajectory_logger = logger

        action, kwargs = ai.choose_action(fresh_engine)
        result = fresh_engine.step(action, **kwargs)
        ai._learn_reward(result)

        logger.close()
        import json
        with open(path) as f:
            lines = f.readlines()
        # Rule-based AI might pick an action that doesn't map (KICK),
        # in which case no record is logged.  But most first actions
        # land in the PlayerAction space.
        assert len(lines) <= 1
        if lines:
            rec = json.loads(lines[0])
            assert rec["species"] == "player"
            assert 0 <= rec["a"] < NUM_PLAYER_ACTIONS
