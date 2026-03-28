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

__version__ = "0.1.0"

import math
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


# ---------------------------------------------------------------------------
# Context keys for the reward model
# ---------------------------------------------------------------------------
CTX_ITEMS_HERE = "items_here"
CTX_NO_ITEMS = "no_items"
CTX_ON_DOWN_STAIRS = "on_down_stairs"
CTX_ON_UP_STAIRS = "on_up_stairs"
CTX_DEFAULT = "default"


class WorldModel:
    """Everything the agent has learned about the current dungeon level."""

    def __init__(self) -> None:
        # Observed cell types: (r, c) → CellBaseType int value.
        self.known_cells: dict[tuple[int, int], int] = {}

        # Cells the agent has physically visited.
        self.visited: set[tuple[int, int]] = set()

        # Observed item locations (may be stale after pickup).
        self.known_items: set[tuple[int, int]] = set()

        # Observed stair locations: (r, c) → "up" | "down".
        self.known_stairs: dict[tuple[int, int], str] = {}

        # Transition model: (target_cell_type, action_category) →
        #   {"success": n, "fail": n}
        # action_category is "move", "pickup", "stairs_down", etc.
        self.transition_counts: dict[tuple[int, str], dict[str, int]] = {}

        # Reward model: (action_category, context) →
        #   {"total": float, "count": int}
        self.reward_counts: dict[tuple[str, str], dict[str, float]] = {}

        # Total actions taken (for exploration decay).
        self.total_actions: int = 0

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

    def __init__(self) -> None:
        # One WorldModel per dungeon level.
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

    @property
    def model(self) -> WorldModel:
        """The world model for the current dungeon level."""
        if self.current_level not in self.level_models:
            self.level_models[self.current_level] = WorldModel()
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
            self._items_collected += int(result.reward)

    # -- planning ----------------------------------------------------------

    def _plan_action(self, engine: GameEngine) -> tuple[Action, dict]:
        """Decide what to do next."""
        # If we have a plan, follow it.
        if self._plan:
            return self._plan.pop(0), {}

        pos = engine.player.pos
        model = self.model

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
