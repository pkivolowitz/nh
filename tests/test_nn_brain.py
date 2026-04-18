# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""Tests for PolicyBrain, RecordingBrain, and TrajectoryLogger."""

from __future__ import annotations

import json
import os

import numpy as np
import pytest

from game.actions import Action
from game.brain import BrainRegistry, JackalBrain, RatBrain
from game.nn_brain import (
    PolicyBrain, RecordingBrain, TrajectoryLogger,
    install_recording_brains,
)
from game.nn_features import NUM_ACTIONS


class TestPolicyBrainFallback:
    """Without a model file, PolicyBrain must still produce a legal action."""

    def test_fallback_to_random_without_model(self, fresh_engine):
        pb = PolicyBrain("rat")  # no model path → no session.
        assert not pb.has_model
        for m in fresh_engine.board.get_all_monsters():
            if m.name == "rat":
                action, _ = pb.choose_action(m, fresh_engine)
                # Must be a member of the Action enum.
                assert isinstance(action, Action)
                return
        pytest.skip("no rat on this seed")

    def test_missing_model_path_does_not_raise(self, tmp_pnh_dir):
        bogus = str(tmp_pnh_dir / "does_not_exist.onnx")
        pb = PolicyBrain("jackal", model_path=bogus)
        assert not pb.has_model

    def test_record_outcome_is_no_op_without_logger(self, fresh_engine):
        pb = PolicyBrain("rat")
        for m in fresh_engine.board.get_all_monsters():
            if m.name == "rat":
                pb.choose_action(m, fresh_engine)
                # Should not raise even without a logger.
                pb.record_outcome(m, Action.WAIT, 0.0, fresh_engine)
                return
        pytest.skip("no rat on this seed")


class TestTrajectoryLogger:
    """Logger must emit well-formed JSON lines."""

    def test_log_writes_record(self, tmp_path):
        path = str(tmp_path / "log.jsonl")
        with TrajectoryLogger(path) as log:
            log.log(
                species="rat",
                features=np.zeros(19, dtype=np.float32),
                action_idx=3,
                reward=0.5,
                next_features=np.ones(19, dtype=np.float32),
                done=False,
                legal_mask=np.ones(NUM_ACTIONS, dtype=bool),
                next_legal_mask=np.ones(NUM_ACTIONS, dtype=bool),
            )
            assert log.count == 1
        # File must be parseable.
        with open(path) as f:
            rec = json.loads(f.readline())
        assert rec["species"] == "rat"
        assert rec["a"] == 3
        assert rec["r"] == 0.5
        assert rec["d"] is False
        assert len(rec["s"]) == 19
        assert len(rec["m"]) == NUM_ACTIONS

    def test_multiple_records_each_one_line(self, tmp_path):
        path = str(tmp_path / "log.jsonl")
        with TrajectoryLogger(path) as log:
            for i in range(5):
                log.log(
                    species="jackal",
                    features=np.zeros(21, dtype=np.float32),
                    action_idx=i % NUM_ACTIONS,
                    reward=float(i),
                    next_features=np.zeros(21, dtype=np.float32),
                    done=bool(i == 4),
                    legal_mask=np.ones(NUM_ACTIONS, dtype=bool),
                    next_legal_mask=np.ones(NUM_ACTIONS, dtype=bool),
                )
        with open(path) as f:
            lines = f.readlines()
        assert len(lines) == 5


class TestRecordingBrain:
    """Wrapping a tabular brain must produce trajectories for every action."""

    def test_recording_brain_logs_one_per_action(self, fresh_engine, tmp_path):
        path = str(tmp_path / "trace.jsonl")
        logger = TrajectoryLogger(path)
        inner = JackalBrain()
        brain = RecordingBrain(inner, "jackal", logger)

        # Construct a fake jackal so we exercise the wrapper even on a
        # level without spawned jackals.
        from game.monster import get_species_registry, Monster
        from game.coordinate import Coordinate
        import random as _r
        spec = get_species_registry()["jackal"]
        jackal = Monster(spec, Coordinate(5, 5), _r.Random(1))

        action, _ = brain.choose_action(jackal, fresh_engine)
        assert hasattr(jackal, "_rec_features")
        assert hasattr(jackal, "_rec_action_idx")

        brain.record_outcome(jackal, action, 0.1, fresh_engine)
        logger.close()
        with open(path) as f:
            lines = f.readlines()
        assert len(lines) == 1
        rec = json.loads(lines[0])
        assert rec["species"] == "jackal"
        assert len(rec["s"]) == 21


class TestInstallRecordingBrains:
    """install_recording_brains must replace registry entries in place."""

    def test_install_swaps_registry_entries(self, tmp_pnh_dir, tmp_path):
        logger = TrajectoryLogger(str(tmp_path / "t.jsonl"))
        install_recording_brains(logger)
        jb = BrainRegistry._brains["jackal"]
        rb = BrainRegistry._brains["rat"]
        assert isinstance(jb, RecordingBrain)
        assert isinstance(rb, RecordingBrain)
        assert isinstance(jb.inner, JackalBrain)
        assert isinstance(rb.inner, RatBrain)
        logger.close()


class TestBrainModeSwitch:
    """BrainRegistry mode must control which brain type is returned."""

    def test_default_mode_is_tabular(self, tmp_pnh_dir):
        BrainRegistry._brains = {}
        BrainRegistry.init(mode="tabular")
        jb = BrainRegistry.get("jackal", JackalBrain)
        assert isinstance(jb, JackalBrain)

    def test_nn_mode_without_model_falls_back(self, tmp_pnh_dir):
        BrainRegistry._brains = {}
        BrainRegistry.init(mode="nn",
                           model_dir=str(tmp_pnh_dir / "no_models"))
        jb = BrainRegistry.get("jackal", JackalBrain)
        # No model file exists — must fall back to tabular type.
        assert isinstance(jb, JackalBrain)

    def test_invalid_mode_raises(self, tmp_pnh_dir):
        with pytest.raises(ValueError):
            BrainRegistry.init(mode="quantum")
