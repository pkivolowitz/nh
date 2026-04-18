# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""Feature extraction — perception dicts → fixed-length float vectors.

The tabular brains use string state keys.  Neural-network brains need
fixed-width float tensors.  This module defines per-species extractors
that convert a brain's ``perceive`` dict into a consistent numpy array
suitable for both ONNX inference and PyTorch training.

Each extractor also knows how to produce an action mask: a boolean
vector over the full 9-action space, True where the monster can
actually execute that action this turn.  The NN outputs Q-values for
all 9 actions; the planner restricts argmax to masked positions.
"""

from __future__ import annotations

__version__ = "0.1.0"

from abc import ABC, abstractmethod
from enum import IntEnum
from typing import TYPE_CHECKING, Optional

import numpy as np

from game.actions import Action, Direction, DIRECTION_DELTA, DIRECTION_TO_ACTION
from game.cell import CellBaseType, DoorState
from game.constants import BOARD_ROWS, BOARD_COLUMNS
from game.coordinate import Coordinate

if TYPE_CHECKING:
    from game.engine import GameEngine
    from game.monster import Monster
    from game.player import Player


# The NN always outputs Q-values over this fixed action space.  Order
# matches the Action enum integer values (WAIT=0, MOVE_N=1, ...).
ACTION_ORDER: list[Action] = [
    Action.WAIT,
    Action.MOVE_N, Action.MOVE_S, Action.MOVE_E, Action.MOVE_W,
    Action.MOVE_NE, Action.MOVE_NW, Action.MOVE_SE, Action.MOVE_SW,
]
NUM_ACTIONS: int = len(ACTION_ORDER)


# ---------------------------------------------------------------------------
# Local vision grid
# ---------------------------------------------------------------------------

# Centered odd-side grid — monster sits at the middle.  7 gives a 3-cell
# radius which is enough to see through a doorway or down a corridor
# without blowing up the feature dimension.
GRID_SIDE: int = 7
GRID_RADIUS: int = GRID_SIDE // 2

# Channel layout (one-hot per cell).  Order matters: feature-dim math
# depends on it.
_GRID_CHANNEL_EMPTY: int = 0
_GRID_CHANNEL_ROOM: int = 1
_GRID_CHANNEL_CORRIDOR: int = 2
_GRID_CHANNEL_WALL: int = 3
_GRID_CHANNEL_DOOR: int = 4
_GRID_CHANNEL_PLAYER: int = 5
_GRID_CHANNEL_OTHER_MONSTER: int = 6
_GRID_CHANNEL_LIT: int = 7
GRID_CHANNELS: int = 8

GRID_DIM: int = GRID_SIDE * GRID_SIDE * GRID_CHANNELS


def _cell_type_to_channel(base_type: CellBaseType) -> int:
    if base_type == CellBaseType.EMPTY:
        return _GRID_CHANNEL_EMPTY
    if base_type == CellBaseType.ROOM:
        return _GRID_CHANNEL_ROOM
    if base_type == CellBaseType.CORRIDOR:
        return _GRID_CHANNEL_CORRIDOR
    if base_type == CellBaseType.WALL:
        return _GRID_CHANNEL_WALL
    if base_type == CellBaseType.DOOR:
        return _GRID_CHANNEL_DOOR
    return _GRID_CHANNEL_EMPTY


def extract_local_grid(monster: Monster,
                       engine: GameEngine) -> np.ndarray:
    """Return a (GRID_SIDE * GRID_SIDE * GRID_CHANNELS,) float32 vector.

    The grid is centered on the monster, with out-of-bounds cells
    encoded as WALL so the network treats edges like solid barriers.
    Channels are one-hot per cell type, plus presence flags for the
    player, other monsters, and lit state.
    """
    grid = np.zeros((GRID_SIDE, GRID_SIDE, GRID_CHANNELS), dtype=np.float32)
    board = engine.board
    player_pos = engine.player.pos

    for gr in range(GRID_SIDE):
        for gc in range(GRID_SIDE):
            br = monster.pos.r + (gr - GRID_RADIUS)
            bc = monster.pos.c + (gc - GRID_RADIUS)
            if not (0 <= br < BOARD_ROWS and 0 <= bc < BOARD_COLUMNS):
                grid[gr, gc, _GRID_CHANNEL_WALL] = 1.0
                continue
            cell = board.cells[br][bc]
            grid[gr, gc, _cell_type_to_channel(cell.base_type)] = 1.0
            if cell.lit:
                grid[gr, gc, _GRID_CHANNEL_LIT] = 1.0
            if br == player_pos.r and bc == player_pos.c:
                grid[gr, gc, _GRID_CHANNEL_PLAYER] = 1.0
            other = board.get_monster_at(Coordinate(br, bc))
            if other is not None and other is not monster:
                grid[gr, gc, _GRID_CHANNEL_OTHER_MONSTER] = 1.0

    return grid.reshape(-1)


# Distance bin buckets — kept in one place so features and tabular
# brains stay consistent.
_DIST_BINS: list[str] = ["adjacent", "close", "medium", "far"]
_HP_BINS: list[str] = ["healthy", "wounded", "critical"]
_PACK_BINS: list[str] = ["alone", "pair", "pack"]
_HEAR_BINS: list[str] = ["silent", "faint", "loud"]
_ESC_BINS: list[str] = ["cornered", "few", "many"]


def _one_hot(value: str, buckets: list[str]) -> list[float]:
    """Return a one-hot list with True at index of *value*."""
    out = [0.0] * len(buckets)
    if value in buckets:
        out[buckets.index(value)] = 1.0
    return out


class FeatureExtractor(ABC):
    """Convert perception + monster state into a fixed-length float vector."""

    feature_dim: int = 0

    @abstractmethod
    def extract(self, monster: Monster, perception: dict,
                engine: GameEngine) -> np.ndarray:
        """Return a 1-D float32 array of length ``feature_dim``."""
        ...

    @staticmethod
    def legal_action_mask(monster: Monster, engine: GameEngine) -> np.ndarray:
        """Boolean mask over ACTION_ORDER marking legal actions this turn.

        Movement is legal into navigable empty cells, into the player's
        cell (bump-attack), but not into other monsters.  WAIT is
        always legal.
        """
        mask = np.zeros(NUM_ACTIONS, dtype=bool)
        mask[0] = True  # WAIT always available.
        for direction, (dr, dc) in DIRECTION_DELTA.items():
            if direction == Direction.NONE:
                continue
            nr, nc = monster.pos.r + dr, monster.pos.c + dc
            if not (0 <= nr < BOARD_ROWS and 0 <= nc < BOARD_COLUMNS):
                continue
            target = Coordinate(nr, nc)
            if target == engine.player.pos:
                mask[ACTION_ORDER.index(DIRECTION_TO_ACTION[direction])] = True
                continue
            if (engine.board.is_navigable(target)
                    and engine.board.get_monster_at(target) is None):
                mask[ACTION_ORDER.index(DIRECTION_TO_ACTION[direction])] = True
        return mask


class JackalFeatures(FeatureExtractor):
    """Jackal-shaped feature vector.

    Layout:
        scalar block (21 floats): perception + HP ratio + distance norm
        spatial block (GRID_DIM floats): 7x7x8 local vision grid
    """

    SCALAR_DIM: int = 21
    feature_dim: int = 21 + GRID_DIM

    _BOARD_DIAG: float = float(np.sqrt(BOARD_ROWS ** 2 + BOARD_COLUMNS ** 2))

    def extract(self, monster: Monster, perception: dict,
                engine: GameEngine) -> np.ndarray:
        can_see = float(bool(perception.get("can_see_prey")))
        dist_oh = _one_hot(perception.get("prey_distance", "far"), _DIST_BINS)
        hp_oh = _one_hot(perception.get("hp", "healthy"), _HP_BINS)
        pack_oh = _one_hot(perception.get("pack", "alone"), _PACK_BINS)
        hear_oh = _one_hot(perception.get("hear", "silent"), _HEAR_BINS)
        ndr, ndc = perception.get("noise_dir", (0, 0))
        smell = float(bool(perception.get("smell", False)))
        sdr, sdc = perception.get("scent_dir", (0, 0))
        hp_ratio = monster.hp / monster.max_hp if monster.max_hp > 0 else 0.0
        raw_dist = monster.pos.distance(engine.player.pos)
        dist_norm = min(1.0, raw_dist / self._BOARD_DIAG)

        scalar = [can_see] + dist_oh + hp_oh + pack_oh + hear_oh
        scalar += [float(ndr), float(ndc), smell, float(sdr), float(sdc)]
        scalar += [hp_ratio, dist_norm]
        scalar_arr = np.asarray(scalar, dtype=np.float32)
        assert scalar_arr.shape == (self.SCALAR_DIM,), \
            f"jackal scalar features got {scalar_arr.shape}"
        grid = extract_local_grid(monster, engine)
        out = np.concatenate([scalar_arr, grid], axis=0)
        assert out.shape == (self.feature_dim,), \
            f"jackal features got {out.shape}, expected ({self.feature_dim},)"
        return out


class RatFeatures(FeatureExtractor):
    """Rat-shaped feature vector.

    Layout:
        scalar block (19 floats): perception + HP ratio + distance norm
        spatial block (GRID_DIM floats): 7x7x8 local vision grid
    """

    SCALAR_DIM: int = 19
    feature_dim: int = 19 + GRID_DIM

    _BOARD_DIAG: float = float(np.sqrt(BOARD_ROWS ** 2 + BOARD_COLUMNS ** 2))

    def extract(self, monster: Monster, perception: dict,
                engine: GameEngine) -> np.ndarray:
        can_see = float(bool(perception.get("can_see_prey")))
        dist_oh = _one_hot(perception.get("prey_distance", "far"), _DIST_BINS)
        hp_oh = _one_hot(perception.get("hp", "healthy"), _HP_BINS)
        food = float(bool(perception.get("food_nearby")))
        fdr, fdc = perception.get("food_dir", (0, 0))
        esc_oh = _one_hot(perception.get("escape", "many"), _ESC_BINS)
        smell_pred = float(bool(perception.get("smell_predator")))
        sdr, sdc = perception.get("scent_dir", (0, 0))
        hp_ratio = monster.hp / monster.max_hp if monster.max_hp > 0 else 0.0
        raw_dist = monster.pos.distance(engine.player.pos)
        dist_norm = min(1.0, raw_dist / self._BOARD_DIAG)

        scalar = [can_see] + dist_oh + hp_oh + [food, float(fdr), float(fdc)]
        scalar += esc_oh + [smell_pred, float(sdr), float(sdc),
                            hp_ratio, dist_norm]
        scalar_arr = np.asarray(scalar, dtype=np.float32)
        assert scalar_arr.shape == (self.SCALAR_DIM,), \
            f"rat scalar features got {scalar_arr.shape}"
        grid = extract_local_grid(monster, engine)
        out = np.concatenate([scalar_arr, grid], axis=0)
        assert out.shape == (self.feature_dim,), \
            f"rat features got {out.shape}, expected ({self.feature_dim},)"
        return out


# Registry: species name → extractor instance.  "player" is included
# so the trainer can consume player trajectories with the same loader
# that handles monster species.
_EXTRACTORS: dict[str, object] = {
    "jackal": JackalFeatures(),
    "rat": RatFeatures(),
}


def get_extractor(species_name: str):
    """Look up the feature extractor for a species.  Raises if unknown.

    The return type is the species-specific FeatureExtractor subclass
    for monsters, or PlayerFeatures for the player.  All extractors
    expose ``feature_dim`` and ``SCALAR_DIM``; monster extractors also
    expose the 9-action ``legal_action_mask`` while PlayerFeatures
    uses the 17-action space.
    """
    if species_name == "player":
        return PlayerFeatures()
    if species_name not in _EXTRACTORS:
        raise KeyError(f"no feature extractor registered for {species_name!r}")
    return _EXTRACTORS[species_name]


# ---------------------------------------------------------------------------
# Player feature extractor & action space
# ---------------------------------------------------------------------------

# The player's grid is larger than the monsters' — they have to plan,
# not just react — and carries more channels because the player cares
# about items, stairs, and lighting that monsters largely ignore.
PLAYER_GRID_SIDE: int = 15
PLAYER_GRID_RADIUS: int = PLAYER_GRID_SIDE // 2

_PGRID_EMPTY: int = 0
_PGRID_ROOM: int = 1
_PGRID_CORRIDOR: int = 2
_PGRID_WALL: int = 3
_PGRID_DOOR_OPEN: int = 4
_PGRID_DOOR_CLOSED: int = 5
_PGRID_MONSTER: int = 6
_PGRID_ITEM: int = 7
_PGRID_STAIRS_DOWN: int = 8
_PGRID_STAIRS_UP: int = 9
_PGRID_LIT: int = 10
PLAYER_GRID_CHANNELS: int = 11
PLAYER_GRID_DIM: int = (
    PLAYER_GRID_SIDE * PLAYER_GRID_SIDE * PLAYER_GRID_CHANNELS
)


class PlayerAction(IntEnum):
    """Compact action space for the player-policy network.

    Indices map 1:1 to network output positions.  The engine-level
    Action and its kwargs are reconstructed by ``decode_player_action``
    — e.g. CAST_FIRE and THROW_ROCK auto-target the nearest visible
    monster.  EAT auto-picks the first food item in inventory.
    """

    WAIT = 0
    MOVE_N = 1
    MOVE_S = 2
    MOVE_E = 3
    MOVE_W = 4
    MOVE_NE = 5
    MOVE_NW = 6
    MOVE_SE = 7
    MOVE_SW = 8
    PICKUP = 9
    STAIRS_DOWN = 10
    STAIRS_UP = 11
    OPEN_N = 12
    OPEN_S = 13
    OPEN_E = 14
    OPEN_W = 15
    CAST_FIRE = 16
    THROW_ROCK = 17
    EAT = 18


NUM_PLAYER_ACTIONS: int = len(PlayerAction)


# Reverse map: PlayerAction → (engine Action, direction).  CAST_FIRE
# is handled specially because it also needs a target coordinate.
_PLAYER_ACTION_MAP: dict[int, tuple[Action, Direction]] = {
    PlayerAction.WAIT: (Action.WAIT, Direction.NONE),
    PlayerAction.MOVE_N: (Action.MOVE_N, Direction.N),
    PlayerAction.MOVE_S: (Action.MOVE_S, Direction.S),
    PlayerAction.MOVE_E: (Action.MOVE_E, Direction.E),
    PlayerAction.MOVE_W: (Action.MOVE_W, Direction.W),
    PlayerAction.MOVE_NE: (Action.MOVE_NE, Direction.NE),
    PlayerAction.MOVE_NW: (Action.MOVE_NW, Direction.NW),
    PlayerAction.MOVE_SE: (Action.MOVE_SE, Direction.SE),
    PlayerAction.MOVE_SW: (Action.MOVE_SW, Direction.SW),
    PlayerAction.PICKUP: (Action.PICKUP, Direction.NONE),
    PlayerAction.STAIRS_DOWN: (Action.STAIRS_DOWN, Direction.NONE),
    PlayerAction.STAIRS_UP: (Action.STAIRS_UP, Direction.NONE),
    PlayerAction.OPEN_N: (Action.OPEN_DOOR, Direction.N),
    PlayerAction.OPEN_S: (Action.OPEN_DOOR, Direction.S),
    PlayerAction.OPEN_E: (Action.OPEN_DOOR, Direction.E),
    PlayerAction.OPEN_W: (Action.OPEN_DOOR, Direction.W),
}


def _nearest_visible_monster(engine: GameEngine) -> Optional[Coordinate]:
    """Closest monster with clear LOS from the player.  None if invisible."""
    from math import inf
    best: Optional[Coordinate] = None
    best_d: float = inf
    player_pos = engine.player.pos
    for m in engine.board.get_all_monsters():
        if not m.is_alive:
            continue
        if not engine.board.line_of_sight(player_pos, m.pos):
            continue
        d = player_pos.distance(m.pos)
        if d < best_d:
            best_d = d
            best = m.pos
    return best


def decode_player_action(pa: int, engine: GameEngine) -> tuple[Action, dict]:
    """Translate a PlayerAction index to (engine Action, kwargs)."""
    from game.magic import MagicSchool
    if pa == PlayerAction.CAST_FIRE:
        target = _nearest_visible_monster(engine)
        if target is None:
            return Action.CAST, {
                "school": MagicSchool.FIRE, "direction": Direction.N,
            }
        return Action.CAST, {
            "school": MagicSchool.FIRE, "target_pos": target,
        }
    if pa == PlayerAction.THROW_ROCK:
        target = _nearest_visible_monster(engine)
        if target is None:
            return Action.THROW_ROCK, {"direction": Direction.N}
        return Action.THROW_ROCK, {"target_pos": target}
    if pa == PlayerAction.EAT:
        return Action.EAT, {}  # Letter-less: engine eats first food.
    action, direction = _PLAYER_ACTION_MAP[pa]
    kwargs: dict = {}
    if direction != Direction.NONE:
        kwargs["direction"] = direction
    return action, kwargs


def _player_cell_channel(cell) -> int:
    """Map a Cell to the primary player-grid channel."""
    if cell.base_type == CellBaseType.EMPTY:
        return _PGRID_EMPTY
    if cell.base_type == CellBaseType.ROOM:
        return _PGRID_ROOM
    if cell.base_type == CellBaseType.CORRIDOR:
        return _PGRID_CORRIDOR
    if cell.base_type == CellBaseType.WALL:
        return _PGRID_WALL
    if cell.base_type == CellBaseType.DOOR:
        if cell.door_state == DoorState.DOOR_CLOSED \
                or cell.door_state == DoorState.DOOR_LOCKED \
                or cell.door_state == DoorState.DOOR_STUCK:
            return _PGRID_DOOR_CLOSED
        return _PGRID_DOOR_OPEN
    return _PGRID_EMPTY


def _extract_player_local_grid(player: Player,
                               engine: GameEngine) -> np.ndarray:
    """15x15x11 one-hot local view around the player."""
    import numpy as _np
    grid = _np.zeros(
        (PLAYER_GRID_SIDE, PLAYER_GRID_SIDE, PLAYER_GRID_CHANNELS),
        dtype=_np.float32,
    )
    board = engine.board
    # Stairs positions so we can mark their channel when visible.
    try:
        down_pos: Optional[Coordinate] = board.downstairs
    except AttributeError:
        down_pos = None
    try:
        up_pos: Optional[Coordinate] = board.upstairs
    except AttributeError:
        up_pos = None

    for gr in range(PLAYER_GRID_SIDE):
        for gc in range(PLAYER_GRID_SIDE):
            br = player.pos.r + (gr - PLAYER_GRID_RADIUS)
            bc = player.pos.c + (gc - PLAYER_GRID_RADIUS)
            if not (0 <= br < BOARD_ROWS and 0 <= bc < BOARD_COLUMNS):
                grid[gr, gc, _PGRID_WALL] = 1.0
                continue
            cell = board.cells[br][bc]
            grid[gr, gc, _player_cell_channel(cell)] = 1.0
            if cell.lit:
                grid[gr, gc, _PGRID_LIT] = 1.0
            coord = Coordinate(br, bc)
            mon = board.get_monster_at(coord)
            if mon is not None and mon.is_alive:
                grid[gr, gc, _PGRID_MONSTER] = 1.0
            if coord in board.goodies and board.goodies[coord]:
                grid[gr, gc, _PGRID_ITEM] = 1.0
            if down_pos is not None and coord == down_pos:
                grid[gr, gc, _PGRID_STAIRS_DOWN] = 1.0
            if up_pos is not None and coord == up_pos:
                grid[gr, gc, _PGRID_STAIRS_UP] = 1.0

    return grid.reshape(-1)


class PlayerFeatures:
    """Feature extractor for the player policy network.

    Layout:
        scalar block (18 floats):
          [0]    HP ratio
          [1]    concentration ratio
          [2]    XP normalized
          [3]    level normalized
          [4:11] 7 school known-flags
          [11]   fire tier normalized
          [12]   weight ratio
          [13]   total item count ratio
          [14]   turn normalized
          [15]   visible monster count ratio
          [16]   rock count normalized (/20)
          [17]   food count normalized (/10)
        spatial block (15x15x11 floats): local one-hot grid.
    """

    SCALAR_DIM: int = 18
    feature_dim: int = 18 + PLAYER_GRID_DIM

    def extract(self, player: Player, engine: GameEngine) -> np.ndarray:
        import numpy as _np
        from game.magic import MagicSchool, ProficiencyTier, TIER_THRESHOLDS
        from game.player import Trait

        hp_max = player.max_hp if player.max_hp > 0 else 1
        hp_ratio = float(player.hp) / hp_max
        con_max = max(1, player.maximum_traits[Trait.CONCENTRATION])
        con_ratio = (
            float(player.current_traits[Trait.CONCENTRATION]) / con_max
        )
        xp = float(player.current_traits[Trait.EXPERIENCE])
        xp_norm = min(1.0, xp / 1000.0)
        lvl = float(player.current_traits[Trait.LEVEL])
        lvl_norm = min(1.0, lvl / 10.0)

        known_flags: list[float] = []
        for school in MagicSchool:
            state = player.magic.schools.get(school)
            known_flags.append(1.0 if (state and state.known) else 0.0)

        fire_state = player.magic.schools[MagicSchool.FIRE]
        fire_tier_norm = float(fire_state.tier) / 4.0 if fire_state.known else 0.0

        weight = player.weight_of_inventory()
        max_wt = max(1, player.max_carry_weight())
        weight_ratio = min(1.0, weight / max_wt)
        items_norm = player.inventory_count() / 52.0
        turn_norm = min(1.0, engine.turn_counter / 2000.0)

        # Count visible monsters (with LOS) to give the NN a
        # coarse "how hot is this room".
        vis_count = 0
        for m in engine.board.get_all_monsters():
            if m.is_alive and engine.board.line_of_sight(player.pos, m.pos):
                vis_count += 1
        vis_norm = min(1.0, vis_count / 5.0)

        # Rock and food counts — the NN's ammo and health pool.
        from game.items import ItemType
        rock_count = 0
        food_count = 0
        for it in player.inventory:
            if it is None:
                continue
            if it.type == ItemType.ROCK:
                rock_count += it.number_of_like_items
            elif it.type == ItemType.FOOD:
                food_count += it.number_of_like_items
        rock_norm = min(1.0, rock_count / 20.0)
        food_norm = min(1.0, food_count / 10.0)

        scalar = [
            hp_ratio, con_ratio, xp_norm, lvl_norm,
            *known_flags,            # 7 floats
            fire_tier_norm,
            weight_ratio, items_norm, turn_norm, vis_norm,
            rock_norm, food_norm,
        ]
        scalar_arr = _np.asarray(scalar, dtype=_np.float32)
        assert scalar_arr.shape == (self.SCALAR_DIM,), (
            f"player scalar got {scalar_arr.shape}, "
            f"expected ({self.SCALAR_DIM},)"
        )
        grid = _extract_player_local_grid(player, engine)
        out = _np.concatenate([scalar_arr, grid], axis=0)
        assert out.shape == (self.feature_dim,), (
            f"player features got {out.shape}, "
            f"expected ({self.feature_dim},)"
        )
        return out

    @staticmethod
    def legal_action_mask(player: Player,
                          engine: GameEngine) -> np.ndarray:
        """Boolean mask over NUM_PLAYER_ACTIONS marking legal actions."""
        from game.magic import MagicSchool, SCHOOL_BASE_COST
        from game.player import Trait

        import numpy as _np
        mask = _np.zeros(NUM_PLAYER_ACTIONS, dtype=bool)
        mask[PlayerAction.WAIT] = True

        # Movement: legal into navigable cells or player-on-monster bump.
        for pa_idx, (a, d) in _PLAYER_ACTION_MAP.items():
            if a not in (Action.MOVE_N, Action.MOVE_S, Action.MOVE_E,
                         Action.MOVE_W, Action.MOVE_NE, Action.MOVE_NW,
                         Action.MOVE_SE, Action.MOVE_SW):
                continue
            dr, dc = DIRECTION_DELTA[d]
            nr, nc = player.pos.r + dr, player.pos.c + dc
            if not (0 <= nr < BOARD_ROWS and 0 <= nc < BOARD_COLUMNS):
                continue
            target = Coordinate(nr, nc)
            cell = engine.board.cells[nr][nc]
            # Closed door → not a normal legal move (must OPEN first).
            if cell.base_type == CellBaseType.DOOR and cell.door_state in (
                DoorState.DOOR_CLOSED,
                DoorState.DOOR_LOCKED,
                DoorState.DOOR_STUCK,
            ):
                continue
            if engine.board.is_navigable(target):
                mask[pa_idx] = True
            elif engine.board.get_monster_at(target) is not None:
                # Melee bump — legal.
                mask[pa_idx] = True

        # PICKUP — items present under the player.
        if player.pos in engine.board.goodies \
                and engine.board.goodies[player.pos]:
            mask[PlayerAction.PICKUP] = True

        # Stairs.
        if engine.board.is_downstairs(player.pos):
            mask[PlayerAction.STAIRS_DOWN] = True
        if engine.board.is_upstairs(player.pos):
            mask[PlayerAction.STAIRS_UP] = True

        # Open door NSEW — closed door in that direction.
        for pa_idx, (a, d) in _PLAYER_ACTION_MAP.items():
            if a != Action.OPEN_DOOR:
                continue
            dr, dc = DIRECTION_DELTA[d]
            nr, nc = player.pos.r + dr, player.pos.c + dc
            if not (0 <= nr < BOARD_ROWS and 0 <= nc < BOARD_COLUMNS):
                continue
            cell = engine.board.cells[nr][nc]
            if cell.base_type == CellBaseType.DOOR and cell.door_state in (
                DoorState.DOOR_CLOSED,
                DoorState.DOOR_LOCKED,
                DoorState.DOOR_STUCK,
            ):
                mask[pa_idx] = True

        # Fire cast — known school, enough concentration, visible target.
        fire = player.magic.schools[MagicSchool.FIRE]
        if fire.known:
            cost = SCHOOL_BASE_COST[MagicSchool.FIRE]
            if player.current_traits[Trait.CONCENTRATION] >= cost:
                if _nearest_visible_monster(engine) is not None:
                    mask[PlayerAction.CAST_FIRE] = True

        # Throw rock — have a rock AND something to throw at.
        from game.items import ItemType
        has_rock = any(
            it is not None and it.type == ItemType.ROCK
            for it in player.inventory
        )
        if has_rock and _nearest_visible_monster(engine) is not None:
            mask[PlayerAction.THROW_ROCK] = True

        # Eat — have food AND HP is not full.
        has_food = any(
            it is not None and it.type == ItemType.FOOD
            for it in player.inventory
        )
        if has_food and player.hp < player.max_hp:
            mask[PlayerAction.EAT] = True

        return mask
