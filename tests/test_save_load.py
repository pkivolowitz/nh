# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""Tests for state persistence: engine save/load and brain save/load."""

from __future__ import annotations

import os

from game.actions import Action
from game.ai_player import PlayerBrain
from game.brain import BrainRegistry, JackalBrain, RatBrain
from game.engine import GameEngine


class TestEnginePersistence:
    """A pickled engine must round-trip with identical observable state."""

    def test_save_creates_file(self, fresh_engine):
        fresh_engine.step(Action.WAIT)
        path = fresh_engine.save()
        assert os.path.exists(path)

    def test_round_trip_preserves_player(self, fresh_engine):
        fresh_engine.step(Action.WAIT)
        fresh_engine.step(Action.WAIT)
        fresh_engine.save()
        restored = GameEngine.load()
        assert restored is not None
        assert restored.player.pos == fresh_engine.player.pos
        assert restored.player.hp == fresh_engine.player.hp
        assert restored.turn_counter == fresh_engine.turn_counter

    def test_load_returns_none_without_save(self, tmp_pnh_dir):
        assert GameEngine.load() is None


class TestJackalBrainPersistence:
    """JackalBrain's Q-table must serialize and deserialize faithfully."""

    def test_empty_brain_saves_and_loads(self, tmp_pnh_dir):
        brain = JackalBrain()
        path = str(tmp_pnh_dir / "jackal.json")
        brain.save(path)
        loaded = JackalBrain.load(path)
        assert loaded.total_experiences == 0
        assert loaded.q_table == {}

    def test_populated_brain_round_trips(self, tmp_pnh_dir):
        brain = JackalBrain()
        brain.q_table["test_state"] = {"3": {"total": 1.5, "count": 10}}
        brain.total_experiences = 42
        path = str(tmp_pnh_dir / "jackal.json")
        brain.save(path)
        loaded = JackalBrain.load(path)
        assert loaded.total_experiences == 42
        # Migration may append |hear=silent suffix to pre-hearing keys.
        matched_key = next(k for k in loaded.q_table.keys() if "test_state" in k)
        assert loaded.q_table[matched_key]["3"]["total"] == 1.5
        assert loaded.q_table[matched_key]["3"]["count"] == 10


class TestRatBrainPersistence:
    def test_round_trip(self, tmp_pnh_dir):
        brain = RatBrain()
        brain.q_table["foo=bar"] = {"1": {"total": -0.3, "count": 5}}
        brain.total_experiences = 7
        path = str(tmp_pnh_dir / "rat.json")
        brain.save(path)
        loaded = RatBrain.load(path)
        assert loaded.total_experiences == 7
        assert loaded.q_table["foo=bar"]["1"]["total"] == -0.3


class TestPlayerBrainPersistence:
    """The AI player's cross-game learning must round-trip."""

    def test_empty_brain_round_trips(self, tmp_pnh_dir):
        brain = PlayerBrain()
        path = str(tmp_pnh_dir / "ai.json")
        brain.save(path)
        loaded = PlayerBrain.load(path)
        assert loaded.total_actions == 0
        assert loaded.transition_counts == {}
        assert loaded.reward_counts == {}

    def test_populated_brain_round_trips(self, tmp_pnh_dir):
        brain = PlayerBrain()
        brain.transition_counts[(1, "move")] = {"success": 100, "fail": 3}
        brain.reward_counts[("move", "default")] = {"total": 0.5, "count": 10}
        brain.total_actions = 500
        brain.games_played = 3
        brain.deaths = 1
        brain.items_collected = 7
        path = str(tmp_pnh_dir / "ai.json")
        brain.save(path)
        loaded = PlayerBrain.load(path)
        assert loaded.transition_counts[(1, "move")] == {"success": 100, "fail": 3}
        assert loaded.reward_counts[("move", "default")]["total"] == 0.5
        assert loaded.total_actions == 500
        assert loaded.games_played == 3
        assert loaded.deaths == 1
        assert loaded.items_collected == 7

    def test_load_missing_file_returns_fresh_brain(self, tmp_pnh_dir):
        path = str(tmp_pnh_dir / "nonexistent.json")
        loaded = PlayerBrain.load(path)
        assert loaded.total_actions == 0
        assert loaded.games_played == 0


class TestBrainRegistry:
    """BrainRegistry.get must lazy-load and cache by species name."""

    def test_get_caches_instance(self, tmp_pnh_dir):
        a = BrainRegistry.get("jackal", JackalBrain)
        b = BrainRegistry.get("jackal", JackalBrain)
        assert a is b

    def test_save_all_persists_all_loaded(self, tmp_pnh_dir):
        j = BrainRegistry.get("jackal", JackalBrain)
        r = BrainRegistry.get("rat", RatBrain)
        j.total_experiences = 99
        r.total_experiences = 11
        BrainRegistry.save_all()
        # Reload by clearing the cache and re-fetching.
        BrainRegistry._brains = {}
        j2 = BrainRegistry.get("jackal", JackalBrain)
        r2 = BrainRegistry.get("rat", RatBrain)
        assert j2.total_experiences == 99
        assert r2.total_experiences == 11
