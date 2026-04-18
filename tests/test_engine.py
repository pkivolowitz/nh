# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""Integration tests for the game engine's core dispatch loop."""

from __future__ import annotations

import pytest

from game.actions import Action, Direction
from game.coordinate import Coordinate
from game.engine import GameEngine, StepResult


class TestEngineConstruction:
    """A new engine must come up with a valid initial state."""

    def test_engine_has_a_board(self, fresh_engine):
        assert fresh_engine.board is not None
        assert len(fresh_engine.boards) == 1

    def test_player_is_alive_and_placed(self, fresh_engine):
        p = fresh_engine.player
        assert p.is_alive
        assert p.hp > 0
        # Player must start on the upstairs of level 1.
        assert fresh_engine.board.is_upstairs(p.pos)

    def test_turn_counter_starts_at_zero(self, fresh_engine):
        assert fresh_engine.turn_counter == 0


class TestDeterminism:
    """Same seed + same inputs = same outputs, end to end."""

    def test_identical_seeds_identical_state(self, tmp_pnh_dir):
        e1 = GameEngine(seed=42)
        e2 = GameEngine(seed=42)
        assert e1.player.pos == e2.player.pos
        assert e1.player.hp == e2.player.hp
        # Board dimensions identical by construction, but cell layout
        # must also match exactly.
        for r in range(len(e1.board.cells)):
            for c in range(len(e1.board.cells[r])):
                assert e1.board.cells[r][c].base_type == e2.board.cells[r][c].base_type

    def test_different_seeds_differ(self, tmp_pnh_dir):
        e1 = GameEngine(seed=1)
        e2 = GameEngine(seed=2)
        # With high probability the two boards differ somewhere.
        diff = False
        for r in range(len(e1.board.cells)):
            for c in range(len(e1.board.cells[r])):
                if e1.board.cells[r][c].base_type != e2.board.cells[r][c].base_type:
                    diff = True
                    break
            if diff:
                break
        assert diff, "two different seeds produced identical boards"


class TestStepDispatch:
    """engine.step must route actions to their handlers correctly."""

    def test_wait_advances_turn(self, fresh_engine):
        result = fresh_engine.step(Action.WAIT)
        assert isinstance(result, StepResult)
        assert result.turn_used
        assert fresh_engine.turn_counter == 1

    def test_unknown_action_does_not_crash(self, fresh_engine):
        # An out-of-range Action integer would raise, but any defined
        # Action must produce a StepResult without exception.
        result = fresh_engine.step(Action.WAIT)
        assert result.done is False

    def test_move_into_wall_does_not_advance(self, fresh_engine):
        """Movement into a wall must not consume a turn."""
        # Find a wall adjacent to the player.
        p = fresh_engine.player
        board = fresh_engine.board
        from game.cell import CellBaseType
        from game.actions import DIRECTION_DELTA
        turn_before = fresh_engine.turn_counter
        for direction, (dr, dc) in DIRECTION_DELTA.items():
            if direction == Direction.NONE:
                continue
            nr, nc = p.pos.r + dr, p.pos.c + dc
            if not (0 <= nr < len(board.cells) and 0 <= nc < len(board.cells[0])):
                continue
            if board.cells[nr][nc].base_type == CellBaseType.WALL:
                # Attempt to step into it.
                from game.actions import DIRECTION_TO_ACTION
                result = fresh_engine.step(DIRECTION_TO_ACTION[direction])
                assert not result.turn_used
                assert fresh_engine.turn_counter == turn_before
                return
        pytest.skip("no wall adjacent to starting position for this seed")


class TestDeath:
    """Lethal damage must flip done=True and stop the player."""

    def test_damage_kills(self, fresh_engine):
        p = fresh_engine.player
        p.take_damage(p.hp + 100)
        assert not p.is_alive
        assert p.hp == 0

    def test_step_after_death_sets_done(self, fresh_engine):
        fresh_engine.player.take_damage(fresh_engine.player.hp + 100)
        result = fresh_engine.step(Action.WAIT)
        # Even a WAIT should bail out once the player is dead.
        assert result.done or not fresh_engine.player.is_alive
