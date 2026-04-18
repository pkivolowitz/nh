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
from typing import TYPE_CHECKING

import numpy as np

from game.actions import Action, Direction, DIRECTION_DELTA, DIRECTION_TO_ACTION
from game.cell import CellBaseType
from game.constants import BOARD_ROWS, BOARD_COLUMNS
from game.coordinate import Coordinate

if TYPE_CHECKING:
    from game.engine import GameEngine
    from game.monster import Monster


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


# Registry: species name → extractor instance.
_EXTRACTORS: dict[str, FeatureExtractor] = {
    "jackal": JackalFeatures(),
    "rat": RatFeatures(),
}


def get_extractor(species_name: str) -> FeatureExtractor:
    """Look up the feature extractor for a species.  Raises if unknown."""
    if species_name not in _EXTRACTORS:
        raise KeyError(f"no feature extractor registered for {species_name!r}")
    return _EXTRACTORS[species_name]
