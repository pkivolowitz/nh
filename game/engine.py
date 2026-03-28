# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""Game engine: turn processing, action execution, and the ML step() interface.

The engine owns the authoritative game state and has *no* curses
dependency.  It can run headless for batch ML training or be driven
interactively through the renderer.
"""

from __future__ import annotations

__version__ = "0.1.0"

import random
from typing import Optional

from game.constants import (
    BOARD_COLUMNS,
    BOARD_ROWS,
    DEFAULT_TORCH_RADIUS,
)
from game.cell import CellBaseType, DoorState
from game.coordinate import Coordinate
from game.board import Board
from game.player import Player
from game.actions import (
    Action, Direction, DIRECTION_DELTA, ACTION_TO_DIRECTION,
)
from game.drawing_support import initialize_corner_map


class StepResult:
    """Return value of ``GameEngine.step``."""

    __slots__ = ("message", "reward", "done", "turn_used")

    def __init__(self, message: str = "", reward: float = 0.0,
                 done: bool = False, turn_used: bool = False) -> None:
        self.message: str = message
        self.reward: float = reward
        self.done: bool = done
        self.turn_used: bool = turn_used


class GameEngine:
    """Pure-logic game engine.

    Public interface
    ----------------
    step(action, **kwargs) → StepResult
        Execute one discrete action and advance game state.
    get_observation() → dict
        Machine-readable snapshot for agents.
    """

    def __init__(self, seed: Optional[int] = None) -> None:
        self.rng: random.Random = random.Random(seed)
        initialize_corner_map()

        self.boards: list[Board] = []
        self.current_board_index: int = 0
        self.turn_counter: int = 0
        self.player: Player = Player(self.rng)

        # Generate the first level.
        self._new_board()
        self.player.pos = Coordinate(
            self.board.upstairs.r, self.board.upstairs.c
        )
        # Mark the player's initial surroundings as known.
        self.board.update_visibility(self.player.pos)

    @property
    def board(self) -> Board:
        """The currently active dungeon level."""
        return self.boards[self.current_board_index]

    # ------------------------------------------------------------------
    # Action dispatch
    # ------------------------------------------------------------------

    def step(self, action: Action, *,
             direction: Direction = Direction.NONE,
             letter: str = "") -> StepResult:
        """Execute *action* and return the result.

        Parameters
        ----------
        action : Action
            The discrete action to take.
        direction : Direction
            Required for OPEN_DOOR / CLOSE_DOOR.
        letter : str
            Required for DROP (inventory letter).
        """
        if action == Action.WAIT:
            self.turn_counter += 1
            result = StepResult(turn_used=True)
        elif action in ACTION_TO_DIRECTION:
            result = self._handle_move(ACTION_TO_DIRECTION[action])
        elif action == Action.STAIRS_DOWN:
            result = self._handle_stairs_down()
        elif action == Action.STAIRS_UP:
            result = self._handle_stairs_up()
        elif action == Action.PICKUP:
            result = self._handle_pickup()
        elif action == Action.DROP:
            result = self._handle_drop(letter)
        elif action == Action.OPEN_DOOR:
            result = self._handle_door(direction, opening=True)
        elif action == Action.CLOSE_DOOR:
            result = self._handle_door(direction, opening=False)
        elif action == Action.KICK_DOOR:
            result = self._handle_kick(direction)
        else:
            result = StepResult(message="Unknown action.")

        # Update visibility from the player's new position so both
        # the renderer and headless agents see consistent is_known.
        self.board.update_visibility(self.player.pos)
        return result

    # ------------------------------------------------------------------
    # Movement
    # ------------------------------------------------------------------

    def _handle_move(self, direction: Direction) -> StepResult:
        """Move the player one step in *direction*."""
        dr, dc = DIRECTION_DELTA[direction]
        target = Coordinate(self.player.pos.r + dr, self.player.pos.c + dc)

        # Bounds check.
        if not (0 <= target.r < BOARD_ROWS and 0 <= target.c < BOARD_COLUMNS):
            return StepResult(message="You can't go there.")

        # Collision check.
        if not self.board.is_navigable(target):
            if self.board.is_door(target):
                cell = self.board.cells[target.r][target.c]
                msgs = {
                    DoorState.DOOR_CLOSED: "The door is closed.",
                    DoorState.DOOR_LOCKED: "This door is locked.",
                    DoorState.DOOR_STUCK: "The door is stuck!",
                }
                return StepResult(message=msgs.get(cell.door_state, ""))
            return StepResult(message="You can't go there.")

        self.player.pos = target
        self.turn_counter += 1

        # Report items on the floor.
        sym = self.board.get_symbol(target)
        msg = ""
        if sym >= 0:
            gc = self.board.get_goodie_count(target)
            noun = "items" if gc > 1 else "item"
            verb = "are" if gc > 1 else "is"
            msg = f"There {verb} {gc} {noun} here."

        return StepResult(message=msg, turn_used=True)

    # ------------------------------------------------------------------
    # Stairs
    # ------------------------------------------------------------------

    def _handle_stairs_down(self) -> StepResult:
        if not self.board.is_downstairs(self.player.pos):
            return StepResult(message="You can't go down here.")
        self.turn_counter += 1
        if self.current_board_index == len(self.boards) - 1:
            self._new_board()
        self.current_board_index += 1
        self.player.pos = Coordinate(
            self.board.upstairs.r, self.board.upstairs.c
        )
        return StepResult(message="You descend the staircase.",
                          turn_used=True)

    def _handle_stairs_up(self) -> StepResult:
        if not self.board.is_upstairs(self.player.pos):
            return StepResult(message="You can't go up here.")
        if self.current_board_index == 0:
            return StepResult(message="You are already on the top level.")
        self.turn_counter += 1
        self.current_board_index -= 1
        self.player.pos = Coordinate(
            self.board.downstairs.r, self.board.downstairs.c
        )
        return StepResult(message="You ascend the staircase.",
                          turn_used=True)

    # ------------------------------------------------------------------
    # Items
    # ------------------------------------------------------------------

    def _handle_pickup(self) -> StepResult:
        items = self.board.remove_goodies(self.player.pos)
        if not items:
            return StepResult(message="There is nothing here to pick up.")

        picked_up = 0
        full = False
        reward = 0.0
        for item in items:
            if full:
                self.board.add_goodie(self.player.pos, item)
                continue
            letter = self.player.add_to_inventory(item)
            if not letter:
                full = True
                self.board.add_goodie(self.player.pos, item)
            else:
                picked_up += 1
                reward += 1.0  # Reward signal for ML agents.

        if picked_up > 0:
            self.turn_counter += 1

        if full:
            msg = "Your pack cannot hold any more."
        else:
            noun = "items" if picked_up > 1 else "item"
            msg = f"Picked up {picked_up} {noun}."

        return StepResult(message=msg, reward=reward,
                          turn_used=picked_up > 0)

    def _handle_drop(self, letter: str) -> StepResult:
        if not letter:
            return StepResult(message="Drop what?")
        item = self.player.remove_from_inventory(letter)
        if item is None:
            return StepResult(message="You don't have that.")
        self.board.add_goodie(self.player.pos, item)
        self.turn_counter += 1
        return StepResult(message=f"Dropped {item.item_name}.",
                          turn_used=True)

    # ------------------------------------------------------------------
    # Doors
    # ------------------------------------------------------------------

    def _handle_door(self, direction: Direction,
                     opening: bool) -> StepResult:
        if direction == Direction.NONE:
            verb = "Open" if opening else "Close"
            return StepResult(message=f"{verb} in what direction?")
        dr, dc = DIRECTION_DELTA[direction]
        target = Coordinate(self.player.pos.r + dr, self.player.pos.c + dc)
        if opening:
            msg = self.board.try_open_door(target)
        else:
            msg = self.board.try_close_door(target)
        turn_used = msg.startswith("You ")
        if turn_used:
            self.turn_counter += 1
        return StepResult(message=msg, turn_used=turn_used)

    def _handle_kick(self, direction: Direction) -> StepResult:
        """Kick a door to force it open."""
        if direction == Direction.NONE:
            return StepResult(message="Kick in what direction?")
        dr, dc = DIRECTION_DELTA[direction]
        target = Coordinate(self.player.pos.r + dr, self.player.pos.c + dc)
        msg = self.board.try_kick_door(target)
        self.turn_counter += 1
        return StepResult(message=msg, turn_used=True)

    # ------------------------------------------------------------------
    # Board management
    # ------------------------------------------------------------------

    def _new_board(self) -> None:
        """Generate and append a new dungeon level."""
        self.boards.append(Board(self.rng))

    # ------------------------------------------------------------------
    # ML observation interface
    # ------------------------------------------------------------------

    def get_observation(self) -> dict:
        """Return the full observable game state for an agent.

        This is the (state) part of the (state, action, reward) tuple.
        """
        return {
            "board": self.board.get_state(),
            "player": self.player.get_state(),
            "turn": self.turn_counter,
            "dungeon_level": self.current_board_index + 1,
        }
