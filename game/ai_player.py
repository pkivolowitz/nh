# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""Model-based learning agent that plays PNH from scratch.

The agent has NO built-in knowledge of game mechanics.  It discovers
that walls block, floors are traversable, pickup yields reward, and
stairs change levels — all from interaction.

Architecture
------------
1. **World map** — built from observations as the agent explores.
2. **Transition model** — tabular: (neighbour_cell_type, action) →
   P(success).  Learned online from every action outcome.
3. **Reward model** — tabular: (context, action) → E[reward].
4. **Planner** — BFS over the learned map toward the highest-value
   goal, weighted by information gain for unexplored cells.
"""

from __future__ import annotations

__version__ = "0.2.0"

import json
import logging
import math
import os
from collections import deque
from typing import Optional

from game.actions import (
    Action, Direction, DIRECTION_DELTA, DIRECTION_TO_ACTION,
    ACTION_TO_DIRECTION,
)
from game.cell import CellBaseType, DoorState
from game.constants import BOARD_ROWS, BOARD_COLUMNS
from game.coordinate import Coordinate
from game.engine import GameEngine, StepResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Context keys for the reward model
# ---------------------------------------------------------------------------
CTX_ITEMS_HERE = "items_here"
CTX_NO_ITEMS = "no_items"
CTX_ON_DOWN_STAIRS = "on_down_stairs"
CTX_ON_UP_STAIRS = "on_up_stairs"
CTX_DEFAULT = "default"


# Persistence path for the AI player's cross-game brain.
AI_BRAIN_PATH: str = "~/.pnh/brains/ai_player.json"

# ONNX model path for the player policy network.
PLAYER_MODEL_PATH: str = "~/.pnh/models/player.onnx"


def _engine_action_to_player_action_idx(action: Action,
                                        kwargs: dict) -> Optional[int]:
    """Map (engine Action, kwargs) back to the PlayerAction enum index.

    Returns None for actions the player-policy action space can't
    represent (e.g. KICK_DOOR) — those transitions are dropped from
    the trajectory log rather than logged with an invalid action.
    """
    from game.actions import Action as _A
    from game.nn_features import PlayerAction

    if action == _A.WAIT:
        return int(PlayerAction.WAIT)
    if action == _A.MOVE_N:
        return int(PlayerAction.MOVE_N)
    if action == _A.MOVE_S:
        return int(PlayerAction.MOVE_S)
    if action == _A.MOVE_E:
        return int(PlayerAction.MOVE_E)
    if action == _A.MOVE_W:
        return int(PlayerAction.MOVE_W)
    if action == _A.MOVE_NE:
        return int(PlayerAction.MOVE_NE)
    if action == _A.MOVE_NW:
        return int(PlayerAction.MOVE_NW)
    if action == _A.MOVE_SE:
        return int(PlayerAction.MOVE_SE)
    if action == _A.MOVE_SW:
        return int(PlayerAction.MOVE_SW)
    if action == _A.PICKUP:
        return int(PlayerAction.PICKUP)
    if action == _A.STAIRS_DOWN:
        return int(PlayerAction.STAIRS_DOWN)
    if action == _A.STAIRS_UP:
        return int(PlayerAction.STAIRS_UP)
    if action == _A.OPEN_DOOR:
        d = kwargs.get("direction")
        if d == Direction.N:
            return int(PlayerAction.OPEN_N)
        if d == Direction.S:
            return int(PlayerAction.OPEN_S)
        if d == Direction.E:
            return int(PlayerAction.OPEN_E)
        if d == Direction.W:
            return int(PlayerAction.OPEN_W)
        return None  # Diagonal door: outside action space.
    if action == _A.CAST:
        from game.magic import MagicSchool
        if kwargs.get("school") == MagicSchool.FIRE:
            return int(PlayerAction.CAST_FIRE)
        return None  # Other schools aren't in the action space yet.
    if action == _A.THROW_ROCK:
        return int(PlayerAction.THROW_ROCK)
    if action == _A.EAT:
        return int(PlayerAction.EAT)
    if action == _A.PRACTICE:
        return int(PlayerAction.PRACTICE)
    return None  # KICK_DOOR, CLOSE_DOOR, READ, DROP — not modelled.


class PlayerBrain:
    """Cross-game persistent knowledge for the AI player.

    The AI's world map (known cells, visited, item locations) is
    per-level and discarded when a new dungeon is generated.  But the
    transition and reward models describe the game *engine* — they
    hold regardless of which dungeon is rolled — so they accumulate
    across every game ever played.  This object owns that learning
    and is saved to disk between runs.
    """

    def __init__(self) -> None:
        # (cell_type, action_category) → {"success": int, "fail": int}
        self.transition_counts: dict[tuple[int, str], dict[str, int]] = {}
        # (action_category, context) → {"total": float, "count": int}
        self.reward_counts: dict[tuple[str, str], dict[str, float]] = {}
        # Lifetime counters.
        self.total_actions: int = 0
        self.games_played: int = 0
        self.deaths: int = 0
        self.items_collected: int = 0

    # -- persistence -------------------------------------------------------

    @staticmethod
    def _encode_tuple_key(key: tuple) -> str:
        """Encode a tuple key as a string for JSON storage."""
        return "|".join(str(k) for k in key)

    def save(self, path: str) -> None:
        """Serialize brain state to JSON."""
        path = os.path.expanduser(path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data: dict = {
            "transition_counts": {
                self._encode_tuple_key(k): v
                for k, v in self.transition_counts.items()
            },
            "reward_counts": {
                self._encode_tuple_key(k): v
                for k, v in self.reward_counts.items()
            },
            "total_actions": self.total_actions,
            "games_played": self.games_played,
            "deaths": self.deaths,
            "items_collected": self.items_collected,
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str) -> PlayerBrain:
        """Load brain state from JSON, returning a fresh brain if absent."""
        brain = cls()
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            return brain
        try:
            with open(path, "r") as f:
                data: dict = json.load(f)
            for k, v in data.get("transition_counts", {}).items():
                ct_str, action_cat = k.split("|", 1)
                brain.transition_counts[(int(ct_str), action_cat)] = v
            for k, v in data.get("reward_counts", {}).items():
                action_cat, context = k.split("|", 1)
                brain.reward_counts[(action_cat, context)] = v
            brain.total_actions = data.get("total_actions", 0)
            brain.games_played = data.get("games_played", 0)
            brain.deaths = data.get("deaths", 0)
            brain.items_collected = data.get("items_collected", 0)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            logger.debug("Failed to load player brain from %s: %s", path, exc)
        return brain


class WorldModel:
    """Per-level map memory, plus shared references to the brain's models.

    Map memory (known cells, visited, item and stair locations) is
    specific to the current dungeon level and is discarded when a new
    dungeon is generated.  Transition and reward counts live on the
    shared ``PlayerBrain`` so they accumulate across games.
    """

    def __init__(self, brain: PlayerBrain) -> None:
        # Per-level map memory — scoped to one dungeon level.
        self.known_cells: dict[tuple[int, int], int] = {}
        self.visited: set[tuple[int, int]] = set()
        self.known_items: set[tuple[int, int]] = set()
        self.known_stairs: dict[tuple[int, int], str] = {}

        # Shared dynamics and reward models live on the brain.
        self._brain: PlayerBrain = brain

    # -- brain-backed properties ------------------------------------------

    @property
    def transition_counts(self) -> dict[tuple[int, str], dict[str, int]]:
        return self._brain.transition_counts

    @property
    def reward_counts(self) -> dict[tuple[str, str], dict[str, float]]:
        return self._brain.reward_counts

    @property
    def total_actions(self) -> int:
        return self._brain.total_actions

    @total_actions.setter
    def total_actions(self, value: int) -> None:
        self._brain.total_actions = value

    # -- model updates -----------------------------------------------------

    def record_transition(self, cell_type: int, action_cat: str,
                          success: bool) -> None:
        """Update the transition model with one observation."""
        key = (cell_type, action_cat)
        entry = self.transition_counts.setdefault(
            key, {"success": 0, "fail": 0}
        )
        entry["success" if success else "fail"] += 1

    def record_reward(self, action_cat: str, context: str,
                      reward: float) -> None:
        """Update the reward model with one observation."""
        key = (action_cat, context)
        entry = self.reward_counts.setdefault(
            key, {"total": 0.0, "count": 0}
        )
        entry["total"] += reward
        entry["count"] += 1

    # -- model queries -----------------------------------------------------

    def p_success(self, cell_type: int, action_cat: str) -> float:
        """Estimated probability that *action_cat* succeeds at *cell_type*.

        Returns 0.5 (maximum uncertainty) for unseen combinations.
        """
        key = (cell_type, action_cat)
        entry = self.transition_counts.get(key)
        if entry is None:
            return 0.5
        total = entry["success"] + entry["fail"]
        if total == 0:
            return 0.5
        return entry["success"] / total

    def expected_reward(self, action_cat: str, context: str) -> float:
        """Expected reward for (*action_cat*, *context*).  0 if unseen."""
        key = (action_cat, context)
        entry = self.reward_counts.get(key)
        if entry is None or entry["count"] == 0:
            return 0.0
        return entry["total"] / entry["count"]

    def is_believed_navigable(self, r: int, c: int) -> bool:
        """Does the learned model predict this cell is traversable?

        Optimistic about uncertainty — untried cell types are assumed
        navigable so the agent explores them rather than avoiding them.
        Only cells with enough evidence of failure are blocked.
        """
        ct = self.known_cells.get((r, c))
        if ct is None:
            return False  # Not yet observed at all.
        # WALL cells are never navigable (learned quickly).
        key = (ct, "move")
        entry = self.transition_counts.get(key)
        if entry is None:
            # Never tried — be optimistic, try it.
            return True
        total = entry["success"] + entry["fail"]
        if total < 3:
            # Not enough data — stay optimistic.
            return True
        return entry["success"] / total > 0.3

    def exploration_value(self, r: int, c: int) -> float:
        """Information gain proxy for visiting (r, c).

        Higher for unvisited cells, and cells adjacent to unknowns.
        Decays as the agent accumulates experience.
        """
        if (r, c) in self.visited:
            # Still some value if neighbours are unknown.
            unknown_neighbours = 0
            for dr in range(-1, 2):
                for dc in range(-1, 2):
                    nr, nc = r + dr, c + dc
                    if (nr, nc) not in self.known_cells:
                        unknown_neighbours += 1
            return 0.1 * unknown_neighbours
        return 1.0


class AIPlayer:
    """A learning agent that plays PNH.

    Call ``choose_action`` each turn.  The agent observes the game
    state, updates its world model, plans toward a goal, and returns
    the next action to take.
    """

    def __init__(self, brain: Optional[PlayerBrain] = None) -> None:
        # Persistent cross-game knowledge.  If omitted, the agent
        # starts fresh — no learning carries over.
        self.brain: PlayerBrain = brain if brain is not None else PlayerBrain()
        # One WorldModel per dungeon level (map memory only).
        self.level_models: dict[int, WorldModel] = {}
        self.current_level: int = 0
        self._plan: list[Action] = []
        self._goal_desc: str = ""
        self._last_pos: Optional[tuple[int, int]] = None
        self._last_action: Optional[Action] = None
        self._last_action_cat: str = ""
        self._last_context: str = ""
        self._items_collected: int = 0
        self._levels_cleared: list[int] = []
        # Trajectory logging for offline NN training.  When set, each
        # action the agent takes is written as a (s, a, r, s', done)
        # record keyed by species="player" so the same trainer that
        # consumes monster logs can consume these.
        self.trajectory_logger: Optional[object] = None
        self._last_engine_ref: Optional[GameEngine] = None
        self._last_features = None
        self._last_mask = None
        self._last_player_action_idx: Optional[int] = None

    @property
    def model(self) -> WorldModel:
        """The world model for the current dungeon level."""
        if self.current_level not in self.level_models:
            self.level_models[self.current_level] = WorldModel(self.brain)
        return self.level_models[self.current_level]

    def choose_action(self, engine: GameEngine) -> tuple[Action, dict]:
        """Observe, learn, plan, act.

        Returns (action, kwargs) suitable for ``engine.step(action, **kwargs)``.
        Also sets ``self.thought`` to a human-readable description of
        what the agent is doing (displayed in the message line).
        """
        obs = engine.get_observation()
        level = obs["dungeon_level"]
        if level != self.current_level:
            self.current_level = level
            self._plan.clear()

        pos = engine.player.pos
        pos_t = (pos.r, pos.c)

        # -- learn from last action's outcome --------------------------
        self._learn_from_outcome(engine, pos_t)

        # -- observe the world -----------------------------------------
        self._observe(engine)

        # -- plan next action ------------------------------------------
        action, kwargs = self._plan_action(engine)

        # -- record what we're about to do ----------------------------
        self._last_pos = pos_t
        self._last_action = action
        self._last_action_cat = self._action_category(action)
        self._last_context = self._get_context(engine)
        self.model.total_actions += 1

        # -- snapshot features for trajectory logging -----------------
        if self.trajectory_logger is not None:
            from game.nn_features import PlayerFeatures
            ext = PlayerFeatures()
            self._last_engine_ref = engine
            self._last_features = ext.extract(engine.player, engine)
            self._last_mask = PlayerFeatures.legal_action_mask(
                engine.player, engine,
            )
            self._last_player_action_idx = _engine_action_to_player_action_idx(
                action, kwargs,
            )

        return action, kwargs

    # -- observation -------------------------------------------------------

    def _observe(self, engine: GameEngine) -> None:
        """Update the world map from the current observation."""
        board = engine.board
        pos = engine.player.pos
        model = self.model
        model.visited.add((pos.r, pos.c))

        # Record all visible cells (within torch range and known).
        for r in range(BOARD_ROWS):
            for c in range(BOARD_COLUMNS):
                cell = board.cells[r][c]
                if cell.is_known:
                    model.known_cells[(r, c)] = int(cell.base_type)

                    # Track items.
                    if board.get_symbol(Coordinate(r, c)) >= 0:
                        model.known_items.add((r, c))
                    else:
                        model.known_items.discard((r, c))

                    # Track stairs.
                    if cell.original_c == ord(">"):
                        model.known_stairs[(r, c)] = "down"
                    elif cell.original_c == ord("<"):
                        model.known_stairs[(r, c)] = "up"

    # -- learning ----------------------------------------------------------

    def _learn_from_outcome(self, engine: GameEngine,
                            current_pos: tuple[int, int]) -> None:
        """Update transition and reward models from the last action."""
        if self._last_action is None:
            return

        model = self.model

        # Did the last action succeed?
        if self._last_action_cat == "move":
            success = current_pos != self._last_pos
            # What cell type were we trying to move into?
            dr, dc = DIRECTION_DELTA.get(
                ACTION_TO_DIRECTION.get(self._last_action, Direction.NONE),
                (0, 0),
            )
            target_r = self._last_pos[0] + dr
            target_c = self._last_pos[1] + dc
            target_ct = model.known_cells.get(
                (target_r, target_c),
                int(CellBaseType.EMPTY),
            )
            model.record_transition(target_ct, "move", success)

        elif self._last_action_cat == "pickup":
            # Success = reward > 0 from the step result.
            # We approximate: if we have more items now, it worked.
            pass  # Handled via reward model below.

        elif self._last_action_cat == "stairs_down":
            success = engine.current_board_index + 1 != self.current_level
            # Actually check if level changed.
            success = (engine.current_board_index + 1) != self._last_level_when_acted \
                if hasattr(self, '_last_level_when_acted') else False

    def _learn_reward(self, result: StepResult) -> None:
        """Record the reward from the last action."""
        if self._last_action is None:
            return
        self.model.record_reward(
            self._last_action_cat, self._last_context, result.reward,
        )
        if result.reward > 0:
            gained: int = int(result.reward)
            self._items_collected += gained
            self.brain.items_collected += gained

        # Trajectory logging — capture (s, a, r, s', done, masks)
        # after engine.step has advanced the world state.
        if (self.trajectory_logger is not None
                and self._last_features is not None
                and self._last_player_action_idx is not None
                and self._last_engine_ref is not None):
            from game.nn_features import (
                PlayerFeatures, NUM_PLAYER_ACTIONS,
            )
            import numpy as _np
            engine = self._last_engine_ref
            if engine.player.is_alive:
                ext = PlayerFeatures()
                next_features = ext.extract(engine.player, engine)
                next_mask = PlayerFeatures.legal_action_mask(
                    engine.player, engine,
                )
                done = bool(result.done)
            else:
                next_features = _np.zeros_like(self._last_features)
                next_mask = _np.zeros(NUM_PLAYER_ACTIONS, dtype=bool)
                done = True
            self.trajectory_logger.log(
                species="player",
                features=self._last_features,
                action_idx=self._last_player_action_idx,
                reward=float(result.reward),
                next_features=next_features,
                done=done,
                legal_mask=self._last_mask,
                next_legal_mask=next_mask,
            )

        # Clear the snapshot so an un-logged action doesn't
        # accidentally reuse stale state.
        self._last_features = None
        self._last_mask = None
        self._last_player_action_idx = None

    # -- planning ----------------------------------------------------------

    def _plan_action(self, engine: GameEngine) -> tuple[Action, dict]:
        """Decide what to do next."""
        # If we have a plan, follow it.
        if self._plan:
            return self._plan.pop(0), {}

        pos = engine.player.pos
        model = self.model

        # Priority 0a: Eat when wounded and food is available.
        from game.items import ItemType
        if engine.player.hp <= engine.player.max_hp // 2:
            has_food = any(
                it is not None and it.type == ItemType.FOOD
                for it in engine.player.inventory
            )
            if has_food:
                self.thought = "Eating to heal"
                return Action.EAT, {}

        # Priority 0.5: Practice magic when safe, full HP, and with
        # concentration reserves.  "Safe" means no monster is visible.
        # This teaches the NN to drill in cleared rooms.
        from game.magic import (
            MagicSchool as _MS, ProficiencyTier, SCHOOL_BASE_COST,
        )
        from game.player import Trait
        drillable_schools = [
            s for s in _MS
            if engine.player.magic.schools[s].known
            and engine.player.magic.schools[s].tier != ProficiencyTier.MASTER
        ]
        if drillable_schools:
            target_school = min(
                drillable_schools,
                key=lambda s: int(engine.player.magic.schools[s].tier),
            )
            practice_cost = max(1, SCHOOL_BASE_COST[target_school] // 2)
            con_cur = engine.player.current_traits[Trait.CONCENTRATION]
            con_max = engine.player.maximum_traits[Trait.CONCENTRATION]
            any_visible_monster = any(
                m.is_alive
                and engine.board.line_of_sight(pos, m.pos)
                for m in engine.board.get_all_monsters()
            )
            hp_full = engine.player.hp == engine.player.max_hp
            # Safe, healthy, reasonably focused → drill.
            if (not any_visible_monster and hp_full
                    and con_cur >= practice_cost
                    and con_cur >= int(con_max * 0.75)):
                self.thought = "Practicing magic"
                return Action.PRACTICE, {}

        # Priority 0b: Throw rocks at a non-adjacent visible monster.
        #   Cheap, safe, and teaches the NN "kite ranged".
        has_rock = any(
            it is not None and it.type == ItemType.ROCK
            for it in engine.player.inventory
        )
        if has_rock:
            target: Optional[Coordinate] = None
            best_d: float = float("inf")
            for m in engine.board.get_all_monsters():
                if not m.is_alive:
                    continue
                if not engine.board.line_of_sight(pos, m.pos):
                    continue
                d = pos.distance(m.pos)
                if d < best_d:
                    best_d = d
                    target = m.pos
            if target is not None and best_d > 1.5:
                self.thought = "Throwing rock"
                return Action.THROW_ROCK, {"target_pos": target}

        # Priority 1: Pick up items if standing on them.
        if (pos.r, pos.c) in model.known_items:
            self.thought = "Picking up item"
            return Action.PICKUP, {}

        # Priority 2: Try to open an adjacent closed door (to expand map).
        door_result = self._try_open_adjacent_door(engine)
        if door_result is not None:
            return door_result

        # Priority 3: If all items collected and downstairs known, go there.
        down_stairs = [(r, c) for (r, c), d in model.known_stairs.items()
                       if d == "down"]
        no_items_left = len(model.known_items) == 0 and self._items_collected > 0
        if down_stairs and no_items_left:
            if (pos.r, pos.c) in down_stairs:
                self.thought = "Level cleared — descending"
                return Action.STAIRS_DOWN, {}
            stair_goal = self._nearest_reachable_goal(
                pos, set(down_stairs), model
            )
            if stair_goal is not None:
                path = self._bfs_path(pos, Coordinate(*stair_goal), model)
                if path:
                    self._plan = path[1:]
                    self.thought = "All items collected — heading to stairs"
                    return path[0], {}

        # Priority 4: Go to known item locations.
        item_goal = self._nearest_reachable_goal(pos, model.known_items, model)
        if item_goal is not None:
            path = self._bfs_path(pos, Coordinate(*item_goal), model)
            if path:
                self._plan = path[1:]
                self.thought = f"Heading to item at r={item_goal[0]} c={item_goal[1]}"
                return path[0], {}

        # Priority 4: Explore — move toward frontier (known cells
        # adjacent to unknown territory).
        frontier = self._find_frontier(pos, model)
        if frontier is not None:
            path = self._bfs_path(pos, Coordinate(*frontier), model)
            if path:
                self._plan = path[1:]
                self.thought = f"Exploring frontier r={frontier[0]} c={frontier[1]}"
                return path[0], {}

        # Priority 5: Explore — visit unvisited known navigable cells.
        explore_goal = self._best_exploration_target(pos, model)
        if explore_goal is not None:
            path = self._bfs_path(pos, Coordinate(*explore_goal), model)
            if path:
                self._plan = path[1:]
                self.thought = f"Exploring r={explore_goal[0]} c={explore_goal[1]}"
                return path[0], {}

        # Priority 6: Push into the unknown — step off the known map
        # from a frontier cell to discover new corridors and rooms.
        push_action = self._push_into_unknown(engine, model)
        if push_action is not None:
            self.thought = "Pushing into unknown territory"
            return push_action, {}

        # Fallback: random navigable step.
        self.thought = "Exploring randomly"
        return self._random_action(engine), {}

    def _try_open_adjacent_door(self, engine: GameEngine
                                ) -> Optional[tuple[Action, dict]]:
        """If there's a non-open door next to us, try to get through it.

        - CLOSED: open normally.
        - STUCK / LOCKED: kick it.
        """
        pos = engine.player.pos
        for direction, (dr, dc) in DIRECTION_DELTA.items():
            if direction == Direction.NONE:
                continue
            nr, nc = pos.r + dr, pos.c + dc
            if not (0 <= nr < BOARD_ROWS and 0 <= nc < BOARD_COLUMNS):
                continue
            cell = engine.board.cells[nr][nc]
            if cell.base_type != CellBaseType.DOOR:
                continue
            if cell.door_state == DoorState.DOOR_CLOSED:
                self.thought = f"Opening door {direction.name}"
                return Action.OPEN_DOOR, {"direction": direction}
            if cell.door_state in (DoorState.DOOR_STUCK,
                                   DoorState.DOOR_LOCKED):
                self.thought = f"Kicking door {direction.name}"
                return Action.KICK_DOOR, {"direction": direction}
        return None

    def _find_frontier(self, pos: Coordinate,
                       model: WorldModel) -> Optional[tuple[int, int]]:
        """Find the nearest navigable cell adjacent to unknown territory.

        The frontier is where the agent needs to stand to push the fog
        of war back and discover corridors, rooms, and items.
        """
        best: Optional[tuple[int, int]] = None
        best_dist = float("inf")

        for (r, c), ct in model.known_cells.items():
            # Must be navigable to walk to.
            if not model.is_believed_navigable(r, c):
                continue
            # Must border at least one unknown cell.
            has_unknown_neighbour = False
            for dr in range(-1, 2):
                for dc in range(-1, 2):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if (nr, nc) not in model.known_cells:
                        has_unknown_neighbour = True
                        break
                if has_unknown_neighbour:
                    break
            if not has_unknown_neighbour:
                continue

            dist = abs(pos.r - r) + abs(pos.c - c)
            if dist < best_dist:
                best_dist = dist
                best = (r, c)

        return best

    def _push_into_unknown(self, engine: GameEngine,
                           model: WorldModel) -> Optional[Action]:
        """Try to step into an unknown cell adjacent to the player.

        When exploration stalls, the agent is at or near the frontier.
        Stepping into an unknown cell may reveal corridors and rooms.
        """
        pos = engine.player.pos
        import random as _rng
        dirs = list(DIRECTION_DELTA.items())
        _rng.shuffle(dirs)
        for direction, (dr, dc) in dirs:
            if direction == Direction.NONE:
                continue
            nr, nc = pos.r + dr, pos.c + dc
            if not (0 <= nr < BOARD_ROWS and 0 <= nc < BOARD_COLUMNS):
                continue
            # Target cell must be navigable in the real board
            # (the agent tries; if it fails, it learns).
            target = Coordinate(nr, nc)
            if (nr, nc) not in model.known_cells:
                # Unknown cell — try it.
                return DIRECTION_TO_ACTION[direction]
            # Also try cells we know are doors (might open them).
            ct = model.known_cells.get((nr, nc))
            if ct == int(CellBaseType.DOOR):
                cell = engine.board.cells[nr][nc]
                if cell.door_state == DoorState.DOOR_CLOSED:
                    # Open it first.
                    return None  # _try_open_adjacent_door handles this.
        return None

    def _nearest_reachable_goal(self, pos: Coordinate,
                                goals: set[tuple[int, int]],
                                model: WorldModel) -> Optional[tuple[int, int]]:
        """Return the nearest goal reachable via BFS, or None."""
        if not goals:
            return None
        best: Optional[tuple[int, int]] = None
        best_dist = float("inf")
        for g in goals:
            d = abs(pos.r - g[0]) + abs(pos.c - g[1])
            if d < best_dist:
                best_dist = d
                best = g
        return best

    def _best_exploration_target(self, pos: Coordinate,
                                 model: WorldModel) -> Optional[tuple[int, int]]:
        """Nearest unvisited navigable known cell."""
        best: Optional[tuple[int, int]] = None
        best_dist = float("inf")

        for (r, c), ct in model.known_cells.items():
            if (r, c) in model.visited:
                continue
            if not model.is_believed_navigable(r, c):
                continue
            dist = abs(pos.r - r) + abs(pos.c - c)
            if dist < best_dist:
                best_dist = dist
                best = (r, c)

        return best

    def _bfs_path(self, start: Coordinate, goal: Coordinate,
                  model: WorldModel) -> list[Action]:
        """BFS over the learned map.  Returns a list of movement actions."""
        if start == goal:
            return []

        visited: set[tuple[int, int]] = set()
        # parent: (r,c) → ((prev_r, prev_c), Action)
        parent: dict[tuple[int, int], tuple[tuple[int, int], Action]] = {}
        queue: deque[tuple[int, int]] = deque()
        start_t = (start.r, start.c)
        goal_t = (goal.r, goal.c)
        queue.append(start_t)
        visited.add(start_t)

        while queue:
            cr, cc = queue.popleft()
            if (cr, cc) == goal_t:
                break

            for direction, (dr, dc) in DIRECTION_DELTA.items():
                if direction == Direction.NONE:
                    continue
                nr, nc = cr + dr, cc + dc
                if (nr, nc) in visited:
                    continue
                if not (0 <= nr < BOARD_ROWS and 0 <= nc < BOARD_COLUMNS):
                    continue

                # Can we traverse this cell according to our model?
                navigable = model.is_believed_navigable(nr, nc)
                # Always allow the goal cell even if we're uncertain.
                if not navigable and (nr, nc) != goal_t:
                    continue

                visited.add((nr, nc))
                action = DIRECTION_TO_ACTION[direction]
                parent[(nr, nc)] = ((cr, cc), action)
                queue.append((nr, nc))
        else:
            # Goal not reached.
            if goal_t not in parent:
                return []

        if goal_t not in parent:
            return []

        # Reconstruct path.
        path: list[Action] = []
        cur = goal_t
        while cur in parent:
            prev, action = parent[cur]
            path.append(action)
            cur = prev
        path.reverse()
        return path

    def _random_action(self, engine: GameEngine) -> Action:
        """Pick a random navigable movement direction."""
        import random
        pos = engine.player.pos
        candidates: list[Action] = []
        for direction, (dr, dc) in DIRECTION_DELTA.items():
            if direction == Direction.NONE:
                continue
            nr, nc = pos.r + dr, pos.c + dc
            if 0 <= nr < BOARD_ROWS and 0 <= nc < BOARD_COLUMNS:
                target = Coordinate(nr, nc)
                if engine.board.is_navigable(target):
                    candidates.append(DIRECTION_TO_ACTION[direction])
        if candidates:
            return random.choice(candidates)
        return Action.WAIT

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _action_category(action: Action) -> str:
        """Broad category string for the transition/reward models."""
        if action in (Action.MOVE_N, Action.MOVE_S, Action.MOVE_E,
                      Action.MOVE_W, Action.MOVE_NE, Action.MOVE_NW,
                      Action.MOVE_SE, Action.MOVE_SW):
            return "move"
        if action == Action.PICKUP:
            return "pickup"
        if action == Action.DROP:
            return "drop"
        if action == Action.STAIRS_DOWN:
            return "stairs_down"
        if action == Action.STAIRS_UP:
            return "stairs_up"
        if action in (Action.OPEN_DOOR, Action.CLOSE_DOOR):
            return "door"
        return "other"

    def _get_context(self, engine: GameEngine) -> str:
        """Context string for the reward model."""
        pos = engine.player.pos
        if engine.board.get_symbol(pos) >= 0:
            return CTX_ITEMS_HERE
        if engine.board.is_downstairs(pos):
            return CTX_ON_DOWN_STAIRS
        if engine.board.is_upstairs(pos):
            return CTX_ON_UP_STAIRS
        return CTX_DEFAULT

    @property
    def thought(self) -> str:
        """What the agent is currently thinking — displayed on screen."""
        return getattr(self, "_thought", "")

    @thought.setter
    def thought(self, value: str) -> None:
        self._thought = value

    @property
    def stats_str(self) -> str:
        """Summary of what the agent has learned."""
        model = self.model
        n_known = len(model.known_cells)
        n_visited = len(model.visited)
        n_items = len(model.known_items)
        n_transitions = sum(
            e["success"] + e["fail"]
            for e in model.transition_counts.values()
        )
        return (
            f"Known:{n_known} Visited:{n_visited} "
            f"Items:{n_items} Transitions:{n_transitions} "
            f"Collected:{self._items_collected}"
        )


# ---------------------------------------------------------------------------
# Neural-network player: ONNX-driven policy
# ---------------------------------------------------------------------------

class PolicyAIPlayer:
    """AI player that drives from an ONNX Q-network.

    Implements the same ``choose_action`` / ``_learn_reward`` interface
    as ``AIPlayer`` so it drops into the existing game loop.  When no
    model file is present it falls back to a masked-random policy —
    the player still moves, just without learned behavior.  Perception
    reuses ``PlayerFeatures``; action decoding reuses the
    ``PlayerAction`` enum from ``nn_features``.
    """

    def __init__(self, model_path: str = PLAYER_MODEL_PATH,
                 epsilon: float = 0.0,
                 brain: Optional[PlayerBrain] = None) -> None:
        self.brain: PlayerBrain = brain if brain is not None else PlayerBrain()
        self._epsilon: float = epsilon
        self._session = None
        self._input_name: Optional[str] = None
        self._output_name: Optional[str] = None
        self.model_path: str = os.path.expanduser(model_path)
        self._try_load_model()
        # Display-only attributes, matched to AIPlayer so the renderer's
        # message line is compatible.
        self._thought: str = ""
        self._items_collected: int = 0
        # Matches AIPlayer's _learn_reward signature.
        self._last_action: Optional[Action] = None

    # -- model loading -----------------------------------------------------

    def _try_load_model(self) -> None:
        """Load the ONNX session; silently degrade to random on failure."""
        import onnxruntime as ort
        if not os.path.exists(self.model_path):
            logger.debug("no player ONNX model at %s; using random fallback",
                         self.model_path)
            return
        try:
            providers = ort.get_available_providers()
            preferred = [p for p in ("CoreMLExecutionProvider",
                                     "CUDAExecutionProvider",
                                     "DmlExecutionProvider")
                         if p in providers]
            preferred.append("CPUExecutionProvider")
            self._session = ort.InferenceSession(
                self.model_path, providers=preferred,
            )
            self._input_name = self._session.get_inputs()[0].name
            self._output_name = self._session.get_outputs()[0].name
            logger.info("PolicyAIPlayer loaded %s with providers %s",
                        self.model_path, self._session.get_providers())
        except Exception as exc:
            logger.warning("failed to load player ONNX model %s: %s",
                           self.model_path, exc)
            self._session = None

    @property
    def has_model(self) -> bool:
        return self._session is not None

    # -- AIPlayer-compatible interface -------------------------------------

    def choose_action(self, engine: GameEngine) -> tuple[Action, dict]:
        """Perceive → forward-pass → mask illegal → decode → execute."""
        import random as _r
        from game.nn_features import (
            PlayerFeatures, NUM_PLAYER_ACTIONS, PlayerAction,
            decode_player_action,
        )
        import numpy as _np

        ext = PlayerFeatures()
        features = ext.extract(engine.player, engine)
        mask = PlayerFeatures.legal_action_mask(engine.player, engine)

        if not mask.any():
            chosen_idx = int(PlayerAction.WAIT)
        elif self._session is None or _r.random() < self._epsilon:
            legal = _np.nonzero(mask)[0]
            chosen_idx = int(_r.choice(legal))
        else:
            q = self._session.run(
                [self._output_name],
                {self._input_name: features.reshape(1, -1)},
            )[0].reshape(-1).copy()
            q[~mask] = -_np.inf
            chosen_idx = int(_np.argmax(q))

        self._last_action = chosen_idx
        self._thought = f"NN picked {PlayerAction(chosen_idx).name}"
        return decode_player_action(chosen_idx, engine)

    def _learn_reward(self, result: StepResult) -> None:
        """Track lifetime items collected; no online NN update."""
        if result.reward > 0:
            gained = int(result.reward)
            self._items_collected += gained
            self.brain.items_collected += gained

    @property
    def thought(self) -> str:
        return self._thought

    @property
    def stats_str(self) -> str:
        return (
            f"NN model={'✓' if self.has_model else '✗'} "
            f"items={self._items_collected}"
        )
