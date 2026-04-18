# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""Monster AI brains with persistent cross-game learning.

Every species has its own Brain subclass whose state persists to disk.
Learning accumulates across all games ever played -- jackals collectively
get smarter over hundreds of runs.

Architecture
------------
- ``Brain`` ABC defines the interface: choose_action, record_outcome,
  save, load.
- ``BrainRegistry`` manages one brain per species, handles persistence.
- ``JackalBrain`` implements canine-appropriate perception and a tabular
  reward model mapping discretized state to average action rewards.
"""

from __future__ import annotations

__version__ = "0.1.0"

import json
import logging
import os
import random as _random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

from game.actions import (
    Action, Direction, DIRECTION_DELTA, DIRECTION_TO_ACTION,
)
from game.constants import (
    BOARD_ROWS, BOARD_COLUMNS,
    NOISE_FAINT_THRESHOLD, NOISE_LOUD_THRESHOLD,
)
from game.coordinate import Coordinate

if TYPE_CHECKING:
    from game.engine import GameEngine
    from game.monster import Monster

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Persistence directory for brain state files.
BRAIN_DIR: str = "~/.pnh/brains"

# Perception distance bins (Euclidean).
DIST_ADJACENT: float = 1.5
DIST_CLOSE: float = 3.0
DIST_MEDIUM: float = 6.0

# Pack detection radius.
PACK_RADIUS: float = 5.0

# Reward signals -- tuned so the brain learns canine-appropriate behavior.
# Dealing damage is the primary positive signal; death is heavily punished.
REWARD_DEAL_DAMAGE_SCALE: float = 1.0
REWARD_MOVE_TOWARD_PREY: float = 0.1
REWARD_MOVE_AWAY_PREY: float = -0.05
REWARD_FAILED_MOVE: float = -0.1
REWARD_WAIT: float = -0.05
REWARD_DEATH: float = -5.0
REWARD_FIRE_NEAR: float = -2.0      # Survived a fire blast — teaches avoidance
REWARD_FIRE_DAMAGE: float = -3.0    # Took fire damage but lived — stronger signal

# Rat-specific reward signals.
REWARD_RAT_FLEE: float = 0.15       # Increased distance from player — good
REWARD_RAT_APPROACH_PREY: float = -0.10  # Got closer to player — bad for a rat
REWARD_RAT_FOOD_CLOSER: float = 0.20    # Moved toward food — strong positive
REWARD_RAT_ON_FOOD: float = 0.50    # Reached food cell — jackpot

# Exploration rate bounds.  Starts high (try everything), decays toward
# a floor as the species accumulates experience across games.
EXPLORATION_MAX: float = 0.30
EXPLORATION_MIN: float = 0.05
EXPLORATION_DECAY_STEPS: int = 10000


# ---------------------------------------------------------------------------
# Brain ABC
# ---------------------------------------------------------------------------

class Brain(ABC):
    """Base class for monster AI.

    One instance per species, shared by all individuals.  Persists
    across games via save/load.
    """

    @abstractmethod
    def choose_action(self, monster: Monster,
                      engine: GameEngine) -> tuple[Action, dict]:
        """Decide what *monster* should do this turn."""
        ...

    @abstractmethod
    def record_outcome(self, monster: Monster, action: Action,
                       reward: float, engine: GameEngine) -> None:
        """Update the learning model with an observed reward."""
        ...

    @abstractmethod
    def save(self, path: str) -> None:
        """Serialize brain state to disk."""
        ...

    @classmethod
    @abstractmethod
    def load(cls, path: str) -> Brain:
        """Deserialize from disk, or create fresh if file is missing."""
        ...


# ---------------------------------------------------------------------------
# Brain registry -- singleton managing one brain per species
# ---------------------------------------------------------------------------

class BrainRegistry:
    """Manages persistent brain instances.

    Call ``init()`` at engine startup.  Call ``save_all()`` at shutdown
    to persist everything learned during the session.

    Mode selection
    --------------
    ``mode`` can be ``"tabular"`` (default) or ``"nn"``.  In ``"nn"``
    mode, ``get()`` returns a ``PolicyBrain`` backed by the species'
    ONNX model if one exists on disk; absent a model, it transparently
    falls back to the tabular brain so the game never stalls on a
    missing file.  The mode can also be selected via the
    ``PNH_BRAIN_MODE`` environment variable.
    """

    _brains: dict[str, Brain] = {}
    _brain_dir: str = ""
    _mode: str = "tabular"
    _model_dir: str = ""

    @classmethod
    def init(cls, brain_dir: str = BRAIN_DIR,
             mode: Optional[str] = None,
             model_dir: Optional[str] = None) -> None:
        """Set persistence directories and the active brain mode.

        ``mode`` precedence: explicit argument > PNH_BRAIN_MODE env var
        > existing mode > default "tabular".
        """
        cls._brain_dir = os.path.expanduser(brain_dir)
        os.makedirs(cls._brain_dir, exist_ok=True)
        env_mode: str = os.environ.get("PNH_BRAIN_MODE", "").strip().lower()
        resolved_mode: str = mode or env_mode or cls._mode or "tabular"
        if resolved_mode not in ("tabular", "nn"):
            raise ValueError(
                f"unknown brain mode {resolved_mode!r} (expected 'tabular' or 'nn')"
            )
        cls._mode = resolved_mode
        from_env = os.environ.get("PNH_MODEL_DIR", "~/.pnh/models")
        cls._model_dir = os.path.expanduser(model_dir or from_env)

    @classmethod
    def get(cls, species_name: str, brain_class: type[Brain]) -> Brain:
        """Get or load the brain for *species_name*, honoring the current mode."""
        if species_name not in cls._brains:
            if cls._mode == "nn":
                cls._brains[species_name] = cls._load_nn(
                    species_name, brain_class,
                )
            else:
                path: str = os.path.join(
                    cls._brain_dir, f"{species_name}.json",
                )
                cls._brains[species_name] = brain_class.load(path)
        return cls._brains[species_name]

    @classmethod
    def _load_nn(cls, species_name: str,
                 tabular_class: type[Brain]) -> Brain:
        """Load a PolicyBrain, falling back to tabular if no model exists."""
        model_path: str = os.path.join(
            cls._model_dir, f"{species_name}.onnx",
        )
        # Local import breaks the circular dependency with nn_brain.
        from game.nn_brain import PolicyBrain
        policy = PolicyBrain(species_name, model_path=model_path)
        if policy.has_model:
            return policy
        # Fallback: ordinary tabular brain loaded from its JSON.
        tab_path: str = os.path.join(cls._brain_dir, f"{species_name}.json")
        return tabular_class.load(tab_path)

    @classmethod
    def save_all(cls) -> None:
        """Persist all loaded brains to disk.

        PolicyBrains have no disk state of their own (models are trained
        offline), so their save() is a no-op.  Tabular brains write their
        Q-tables as before.
        """
        for name, brain in cls._brains.items():
            path: str = os.path.join(cls._brain_dir, f"{name}.json")
            brain.save(path)

    @classmethod
    def mode(cls) -> str:
        return cls._mode


# ---------------------------------------------------------------------------
# Jackal brain -- canine intelligence
# ---------------------------------------------------------------------------

class JackalBrain(Brain):
    """Canine-intelligence brain.

    Perceives the world through instinct-appropriate senses: can I see
    prey?  How far?  Am I hurt?  Are packmates nearby?

    Learning is tabular: discretized perception state x action -> running
    average reward.  The Q-table persists across games so the species
    collectively improves over hundreds of playthroughs.

    Pack coordination is not hard-coded -- it emerges from the brain
    observing that attacking with packmates nearby yields better outcomes
    (more damage dealt, less dying).
    """

    def __init__(self) -> None:
        # Q-table: state_key -> {action_key: {"total": float, "count": int}}
        self.q_table: dict[str, dict[str, dict[str, float]]] = {}
        self.total_experiences: int = 0

    @property
    def exploration_rate(self) -> float:
        """Epsilon for epsilon-greedy, decays with accumulated experience."""
        decay: float = EXPLORATION_MAX - EXPLORATION_MIN
        progress: float = min(1.0, self.total_experiences / EXPLORATION_DECAY_STEPS)
        return EXPLORATION_MAX - decay * progress

    # -- perception --------------------------------------------------------

    def perceive(self, monster: Monster,
                 engine: GameEngine) -> dict:
        """Build canine-appropriate perception of the world.

        A jackal perceives: prey visibility (gated by sight_radius)
        and distance, own health, nearby packmates, audible noise
        (with direction), and scent — a directional vector toward
        the player when within smell_radius, penetrating walls.
        Sight and smell are independent senses.
        """
        player = engine.player
        board = engine.board
        senses = monster.senses

        # Distance to prey (needed for sight gating and scent).
        dist: float = monster.pos.distance(player.pos)

        # Can I see prey?  Requires LOS and that the prey is within
        # sight range — and that range depends on whether the prey's
        # cell is lit.  Jackals have strong dark vision; rats don't.
        has_los: bool = board.line_of_sight(monster.pos, player.pos)
        target_lit: bool = board.cells[player.pos.r][player.pos.c].lit
        can_see: bool = has_los and dist <= senses.sight_radius(target_lit)
        if dist <= DIST_ADJACENT:
            dist_bin: str = "adjacent"
        elif dist <= DIST_CLOSE:
            dist_bin = "close"
        elif dist <= DIST_MEDIUM:
            dist_bin = "medium"
        else:
            dist_bin = "far"

        # Own health (binned).
        hp_ratio: float = monster.hp / monster.max_hp if monster.max_hp > 0 else 0.0
        if hp_ratio > 0.75:
            hp_bin: str = "healthy"
        elif hp_ratio > 0.25:
            hp_bin = "wounded"
        else:
            hp_bin = "critical"

        # Pack: count same-species within detection radius.
        pack_count: int = 0
        for m in board.get_monsters_near(monster.pos, PACK_RADIUS):
            if m is not monster and m.species is monster.species:
                pack_count += 1
        if pack_count == 0:
            pack_bin: str = "alone"
        elif pack_count == 1:
            pack_bin = "pair"
        else:
            pack_bin = "pack"

        # Hearing: what's the loudest audible noise and from where?
        noise_level, noise_source = board.noise_at(monster.pos)
        if noise_level >= NOISE_LOUD_THRESHOLD:
            hear_bin: str = "loud"
        elif noise_level >= NOISE_FAINT_THRESHOLD:
            hear_bin = "faint"
        else:
            hear_bin = "silent"

        # Direction (sign only) to the loudest source.
        if noise_source is not None and hear_bin != "silent":
            ndr: int = ((noise_source.r > monster.pos.r)
                        - (noise_source.r < monster.pos.r))
            ndc: int = ((noise_source.c > monster.pos.c)
                        - (noise_source.c < monster.pos.c))
        else:
            ndr = 0
            ndc = 0

        # Scent: directional vector toward prey if within smell range.
        # Smell penetrates walls — the jackal can track unseen prey.
        smell_detected: bool = dist <= senses.smell_radius()
        if smell_detected:
            sdr: int = ((player.pos.r > monster.pos.r)
                        - (player.pos.r < monster.pos.r))
            sdc: int = ((player.pos.c > monster.pos.c)
                        - (player.pos.c < monster.pos.c))
        else:
            sdr = 0
            sdc = 0

        return {
            "can_see_prey": can_see,
            "prey_distance": dist_bin,
            "hp": hp_bin,
            "pack": pack_bin,
            "hear": hear_bin,
            "noise_dir": (ndr, ndc),
            "smell": smell_detected,
            "scent_dir": (sdr, sdc),
        }

    def _state_key(self, perception: dict) -> str:
        """Discretize perception into a hashable Q-table key.

        The hearing and scent dimensions each append their direction
        only when the sense is active, keeping the silent/no-scent
        state space small while letting the brain learn
        direction-dependent responses.
        """
        base: str = (
            f"see={perception['can_see_prey']}"
            f"|dist={perception['prey_distance']}"
            f"|hp={perception['hp']}"
            f"|pack={perception['pack']}"
            f"|hear={perception['hear']}"
        )
        if perception["hear"] != "silent":
            ndr, ndc = perception["noise_dir"]
            base += f"|ndir=({ndr},{ndc})"
        if perception["smell"]:
            sdr, sdc = perception["scent_dir"]
            base += f"|scent=({sdr},{sdc})"
        return base

    # -- action selection --------------------------------------------------

    def choose_action(self, monster: Monster,
                      engine: GameEngine) -> tuple[Action, dict]:
        """Decide what this jackal should do this turn."""
        perception: dict = self.perceive(monster, engine)
        state: str = self._state_key(perception)

        # Store state for reward attribution when outcome arrives.
        monster.last_state_key = state

        actions: list[Action] = self._available_actions(monster, engine)
        if not actions:
            return Action.WAIT, {}

        # Epsilon-greedy: explore or exploit.
        if _random.random() < self.exploration_rate:
            chosen: Action = _random.choice(actions)
        else:
            chosen = self._best_action(state, actions)

        return chosen, {}

    def _best_action(self, state: str,
                     actions: list[Action]) -> Action:
        """Pick the action with the highest average reward."""
        q_state: dict = self.q_table.get(state, {})
        best_val: float = float("-inf")
        best_action: Action = actions[0]

        for a in actions:
            a_key: str = str(int(a))
            entry: dict = q_state.get(a_key, {"total": 0.0, "count": 0})
            val: float = entry["total"] / entry["count"] if entry["count"] > 0 else 0.0
            if val > best_val:
                best_val = val
                best_action = a

        return best_action

    def _available_actions(self, monster: Monster,
                           engine: GameEngine) -> list[Action]:
        """Actions a jackal can take right now.

        Jackals can move in 8 directions (into navigable cells or
        the player's cell for an attack) or wait.  They cannot open
        doors, pick up items, or use stairs.
        """
        actions: list[Action] = [Action.WAIT]

        for direction in Direction:
            if direction == Direction.NONE:
                continue
            dr, dc = DIRECTION_DELTA[direction]
            nr: int = monster.pos.r + dr
            nc: int = monster.pos.c + dc
            if not (0 <= nr < BOARD_ROWS and 0 <= nc < BOARD_COLUMNS):
                continue

            target: Coordinate = Coordinate(nr, nc)

            # Player at target = attack opportunity (resolved by engine).
            if target == engine.player.pos:
                actions.append(DIRECTION_TO_ACTION[direction])
                continue

            # Navigable and not occupied by another monster.
            if (engine.board.is_navigable(target)
                    and engine.board.get_monster_at(target) is None):
                actions.append(DIRECTION_TO_ACTION[direction])

        return actions

    # -- learning ----------------------------------------------------------

    def record_outcome(self, monster: Monster, action: Action,
                       reward: float, engine: GameEngine) -> None:
        """Record reward for the (state, action) pair.

        Uses the state stored in ``monster.last_state_key`` (set during
        ``choose_action``) so the reward is attributed to the perception
        that produced the decision, not the current (possibly post-death)
        perception.
        """
        state: str = (monster.last_state_key
                      or self._state_key(self.perceive(monster, engine)))
        a_key: str = str(int(action))

        q_state: dict = self.q_table.setdefault(state, {})
        entry: dict = q_state.setdefault(
            a_key, {"total": 0.0, "count": 0}
        )
        entry["total"] += reward
        entry["count"] += 1
        self.total_experiences += 1

    # -- persistence -------------------------------------------------------

    def save(self, path: str) -> None:
        """Write brain state to JSON."""
        data: dict = {
            "q_table": self.q_table,
            "total_experiences": self.total_experiences,
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str) -> JackalBrain:
        """Load brain state from JSON, or create fresh if not found.

        Migrates old keys that pre-date the hearing dimension: any
        key without ``|hear=`` is assumed to represent silent states
        and is rewritten with ``|hear=silent`` appended.  This preserves
        learning from games played before the noise system existed.
        """
        brain: JackalBrain = cls()
        if not os.path.exists(path):
            return brain
        try:
            with open(path, "r") as f:
                data: dict = json.load(f)
            raw_q: dict = data.get("q_table", {})
            migrated: dict[str, dict[str, dict[str, float]]] = {}
            for key, val in raw_q.items():
                new_key: str = key
                if "|hear=" not in new_key and "hear=" not in new_key:
                    new_key = f"{new_key}|hear=silent"
                migrated[new_key] = val
            brain.q_table = migrated
            brain.total_experiences = data.get("total_experiences", 0)
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.debug("Failed to load brain from %s: %s", path, exc)
        return brain


# ---------------------------------------------------------------------------
# Rat brain -- cowardly scavenger
# ---------------------------------------------------------------------------

class RatBrain(Brain):
    """Rodent-intelligence brain.

    Rats are the opposite of jackals: they flee the player, seek
    food on the floor, and only bite when cornered.  Learning is
    the same tabular Q-table but with reward signals tuned for
    scavenging and survival, not aggression.

    Perception axes:
        can_see_prey (bool): player is visible
        prey_distance (binned): how close the danger is
        hp (binned): own health
        food_nearby (bool): any food within sense radius
        food_direction (dr, dc): sign-only direction to nearest food
        escape_routes (int): how many adjacent cells lead away from player
    """

    def __init__(self) -> None:
        self.q_table: dict[str, dict[str, dict[str, float]]] = {}
        self.total_experiences: int = 0

    @property
    def exploration_rate(self) -> float:
        """Epsilon for epsilon-greedy, decays with experience."""
        decay: float = EXPLORATION_MAX - EXPLORATION_MIN
        progress: float = min(1.0, self.total_experiences / EXPLORATION_DECAY_STEPS)
        return EXPLORATION_MAX - decay * progress

    # -- perception --------------------------------------------------------

    def perceive(self, monster: Monster,
                 engine: GameEngine) -> dict:
        """Build rodent-appropriate perception of the world.

        A rat perceives: danger visibility (gated by poor sight_radius)
        and distance, own health, scent of predator (directional,
        through walls), whether food is within smell range and which
        direction it lies, and how many escape routes exist.  Rats see
        poorly but smell extraordinarily well.
        """
        player = engine.player
        board = engine.board
        senses = monster.senses

        # Distance to predator (needed for sight gating, scent, and binning).
        dist: float = monster.pos.distance(player.pos)

        # Can I see the predator?  Rat vision is terrible even with LOS
        # and falls off further when the target cell is unlit.
        has_los: bool = board.line_of_sight(monster.pos, player.pos)
        target_lit: bool = board.cells[player.pos.r][player.pos.c].lit
        can_see: bool = has_los and dist <= senses.sight_radius(target_lit)
        if dist <= DIST_ADJACENT:
            dist_bin: str = "adjacent"
        elif dist <= DIST_CLOSE:
            dist_bin = "close"
        elif dist <= DIST_MEDIUM:
            dist_bin = "medium"
        else:
            dist_bin = "far"

        # Own health (binned).
        hp_ratio: float = monster.hp / monster.max_hp if monster.max_hp > 0 else 0.0
        if hp_ratio > 0.75:
            hp_bin: str = "healthy"
        elif hp_ratio > 0.25:
            hp_bin = "wounded"
        else:
            hp_bin = "critical"

        # Food detection: find nearest food within smell radius.
        # The rat's nose is its primary food-finding sense.
        smell_r: float = senses.smell_radius()
        food_nearby: bool = False
        food_dr: int = 0
        food_dc: int = 0
        best_food_dist: float = smell_r + 1
        from game.items import ItemType
        for coord, items in board.goodies.items():
            for item in items:
                if item.type == ItemType.FOOD:
                    fd: float = monster.pos.distance(coord)
                    if fd < best_food_dist:
                        best_food_dist = fd
                        food_nearby = True
                        food_dr = ((coord.r > monster.pos.r)
                                   - (coord.r < monster.pos.r))
                        food_dc = ((coord.c > monster.pos.c)
                                   - (coord.c < monster.pos.c))
                    break  # One food item per cell is enough.

        # Predator scent: directional awareness of the player even
        # when unseen.  Rats' extraordinary smell lets them avoid
        # predators before they're visible.
        smell_predator: bool = dist <= smell_r
        if smell_predator:
            sdr: int = ((player.pos.r > monster.pos.r)
                        - (player.pos.r < monster.pos.r))
            sdc: int = ((player.pos.c > monster.pos.c)
                        - (player.pos.c < monster.pos.c))
        else:
            sdr = 0
            sdc = 0

        # Escape routes: adjacent navigable cells that increase distance
        # from the player.
        escape_count: int = 0
        for direction in Direction:
            if direction == Direction.NONE:
                continue
            dr, dc = DIRECTION_DELTA[direction]
            nr: int = monster.pos.r + dr
            nc: int = monster.pos.c + dc
            if not (0 <= nr < BOARD_ROWS and 0 <= nc < BOARD_COLUMNS):
                continue
            target: Coordinate = Coordinate(nr, nc)
            if target == player.pos:
                continue
            if (board.is_navigable(target)
                    and board.get_monster_at(target) is None):
                new_dist: float = target.distance(player.pos)
                if new_dist > dist:
                    escape_count += 1

        if escape_count == 0:
            escape_bin: str = "cornered"
        elif escape_count <= 2:
            escape_bin = "few"
        else:
            escape_bin = "many"

        return {
            "can_see_prey": can_see,
            "prey_distance": dist_bin,
            "hp": hp_bin,
            "food_nearby": food_nearby,
            "food_dir": (food_dr, food_dc),
            "escape": escape_bin,
            "smell_predator": smell_predator,
            "scent_dir": (sdr, sdc),
        }

    def _state_key(self, perception: dict) -> str:
        """Discretize perception into a Q-table key.

        Food-direction and predator-scent are each appended only when
        that sense is active, keeping the state space compact.
        """
        base: str = (
            f"see={perception['can_see_prey']}"
            f"|dist={perception['prey_distance']}"
            f"|hp={perception['hp']}"
            f"|food={perception['food_nearby']}"
            f"|esc={perception['escape']}"
        )
        if perception["food_nearby"]:
            fdr, fdc = perception["food_dir"]
            base += f"|fdir=({fdr},{fdc})"
        if perception["smell_predator"]:
            sdr, sdc = perception["scent_dir"]
            base += f"|scent=({sdr},{sdc})"
        return base

    # -- action selection --------------------------------------------------

    def choose_action(self, monster: Monster,
                      engine: GameEngine) -> tuple[Action, dict]:
        """Decide what this rat should do this turn."""
        perception: dict = self.perceive(monster, engine)
        state: str = self._state_key(perception)
        monster.last_state_key = state

        actions: list[Action] = self._available_actions(monster, engine)
        if not actions:
            return Action.WAIT, {}

        if _random.random() < self.exploration_rate:
            chosen: Action = _random.choice(actions)
        else:
            chosen = self._best_action(state, actions)

        return chosen, {}

    def _best_action(self, state: str,
                     actions: list[Action]) -> Action:
        """Pick the action with the highest average reward."""
        q_state: dict = self.q_table.get(state, {})
        best_val: float = float("-inf")
        best_action: Action = actions[0]
        for a in actions:
            a_key: str = str(int(a))
            entry: dict = q_state.get(a_key, {"total": 0.0, "count": 0})
            val: float = entry["total"] / entry["count"] if entry["count"] > 0 else 0.0
            if val > best_val:
                best_val = val
                best_action = a
        return best_action

    def _available_actions(self, monster: Monster,
                           engine: GameEngine) -> list[Action]:
        """Actions a rat can take.

        Rats can move in 8 directions (or attack the player if
        adjacent — cornered bite) or wait.  They cannot open doors,
        pick up items, or use stairs.
        """
        actions: list[Action] = [Action.WAIT]
        for direction in Direction:
            if direction == Direction.NONE:
                continue
            dr, dc = DIRECTION_DELTA[direction]
            nr: int = monster.pos.r + dr
            nc: int = monster.pos.c + dc
            if not (0 <= nr < BOARD_ROWS and 0 <= nc < BOARD_COLUMNS):
                continue
            target: Coordinate = Coordinate(nr, nc)
            if target == engine.player.pos:
                actions.append(DIRECTION_TO_ACTION[direction])
                continue
            if (engine.board.is_navigable(target)
                    and engine.board.get_monster_at(target) is None):
                actions.append(DIRECTION_TO_ACTION[direction])
        return actions

    # -- learning ----------------------------------------------------------

    def record_outcome(self, monster: Monster, action: Action,
                       reward: float, engine: GameEngine) -> None:
        """Record reward for the (state, action) pair."""
        state: str = (monster.last_state_key
                      or self._state_key(self.perceive(monster, engine)))
        a_key: str = str(int(action))
        q_state: dict = self.q_table.setdefault(state, {})
        entry: dict = q_state.setdefault(
            a_key, {"total": 0.0, "count": 0}
        )
        entry["total"] += reward
        entry["count"] += 1
        self.total_experiences += 1

    # -- persistence -------------------------------------------------------

    def save(self, path: str) -> None:
        """Write brain state to JSON."""
        data: dict = {
            "q_table": self.q_table,
            "total_experiences": self.total_experiences,
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str) -> RatBrain:
        """Load brain state from JSON, or create fresh if not found."""
        brain: RatBrain = cls()
        if not os.path.exists(path):
            return brain
        try:
            with open(path, "r") as f:
                data: dict = json.load(f)
            brain.q_table = data.get("q_table", {})
            brain.total_experiences = data.get("total_experiences", 0)
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.debug("Failed to load rat brain from %s: %s", path, exc)
        return brain
