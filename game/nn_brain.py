# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""Neural-network-driven monster brain.

A ``PolicyBrain`` fulfils the ``Brain`` contract using an ONNX model as
its Q-function.  Perception is still produced by the species'
tabular brain (``JackalBrain`` / ``RatBrain``) — we only replace the
decision and learning stages.  This keeps the sensory computation in
one place and lets the NN brain start from the same observations the
tabular code was tuned on.

Learning is offline: ``record_outcome`` logs experience tuples to a
``TrajectoryLogger`` (if configured).  A separate PyTorch training
loop consumes those logs, fits a policy, and exports a fresh .onnx
model.  The game itself only runs ONNX inference.
"""

from __future__ import annotations

__version__ = "0.1.0"

import logging
import os
import random as _random
from typing import Optional, TYPE_CHECKING

import numpy as np

from game.brain import Brain, EXPLORATION_MIN, JackalBrain, RatBrain
from game.nn_features import (
    FeatureExtractor, get_extractor,
    ACTION_ORDER, NUM_ACTIONS,
)

if TYPE_CHECKING:
    from game.actions import Action
    from game.engine import GameEngine
    from game.monster import Monster

logger = logging.getLogger(__name__)


# Default directory for ONNX model files.
MODEL_DIR: str = "~/.pnh/models"


class TrajectoryLogger:
    """Append-only log of experience tuples for offline training.

    Each entry captures (features, action_index, reward, next_features,
    done, legal_mask, next_legal_mask) — everything a downstream RL
    trainer needs to fit Q-learning or policy-gradient objectives.
    """

    def __init__(self, path: str) -> None:
        self.path: str = os.path.expanduser(path)
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self._fh = open(self.path, "a")
        self._count: int = 0

    def log(self, species: str, features: np.ndarray, action_idx: int,
            reward: float, next_features: np.ndarray,
            done: bool, legal_mask: np.ndarray,
            next_legal_mask: np.ndarray) -> None:
        import json
        rec = {
            "species": species,
            "s": features.tolist(),
            "a": int(action_idx),
            "r": float(reward),
            "sp": next_features.tolist(),
            "d": bool(done),
            "m": [bool(x) for x in legal_mask],
            "mp": [bool(x) for x in next_legal_mask],
        }
        self._fh.write(json.dumps(rec) + "\n")
        self._count += 1

    @property
    def count(self) -> int:
        return self._count

    def close(self) -> None:
        if not self._fh.closed:
            self._fh.flush()
            self._fh.close()

    def __enter__(self) -> TrajectoryLogger:
        return self

    def __exit__(self, *a) -> None:
        self.close()


class RecordingBrain(Brain):
    """Wraps a tabular brain to log (s, a, r, s', done) tuples.

    The inner brain keeps learning in its tabular Q-table exactly as
    before — the wrapper is transparent to game code.  After each
    action is chosen and each outcome recorded, the wrapper also
    computes NN features and appends a training record to the logger.
    """

    def __init__(self, inner: Brain, species_name: str,
                 logger: TrajectoryLogger) -> None:
        self.inner: Brain = inner
        self.species_name: str = species_name
        self.extractor: FeatureExtractor = get_extractor(species_name)
        self.logger: TrajectoryLogger = logger

    # Expose attributes of the inner brain so existing code that reads
    # q_table / total_experiences / exploration_rate keeps working.
    def __getattr__(self, name: str):
        return getattr(self.inner, name)

    def choose_action(self, monster: Monster,
                      engine: GameEngine) -> tuple[Action, dict]:
        # Capture features *before* the inner brain runs, using its
        # perception path so the features reflect the same observation
        # the tabular policy saw.
        perception = self.inner.perceive(monster, engine)
        features = self.extractor.extract(monster, perception, engine)
        mask = FeatureExtractor.legal_action_mask(monster, engine)

        # The inner brain will call perceive() again internally; that's
        # a cheap cost for keeping the wrapper non-invasive.
        action, kwargs = self.inner.choose_action(monster, engine)

        monster._rec_features = features
        monster._rec_mask = mask
        try:
            monster._rec_action_idx = ACTION_ORDER.index(action)
        except ValueError:
            monster._rec_action_idx = 0
        return action, kwargs

    def record_outcome(self, monster: Monster, action: Action,
                       reward: float, engine: GameEngine) -> None:
        # Always defer to the inner brain for tabular learning.
        self.inner.record_outcome(monster, action, reward, engine)
        if not hasattr(monster, "_rec_features"):
            return
        if monster.is_alive:
            next_perception = self.inner.perceive(monster, engine)
            next_features = self.extractor.extract(
                monster, next_perception, engine,
            )
            next_mask = FeatureExtractor.legal_action_mask(monster, engine)
            done = False
        else:
            next_features = np.zeros_like(monster._rec_features)
            next_mask = np.zeros(NUM_ACTIONS, dtype=bool)
            done = True
        self.logger.log(
            species=self.species_name,
            features=monster._rec_features,
            action_idx=monster._rec_action_idx,
            reward=reward,
            next_features=next_features,
            done=done,
            legal_mask=monster._rec_mask,
            next_legal_mask=next_mask,
        )

    def save(self, path: str) -> None:
        self.inner.save(path)

    @classmethod
    def load(cls, path: str) -> Brain:
        raise NotImplementedError(
            "RecordingBrain wraps an already-loaded inner brain; "
            "construct it directly rather than calling load()."
        )


def install_recording_brains(logger: TrajectoryLogger,
                             species_names: Optional[list[str]] = None) -> None:
    """Replace BrainRegistry's loaded brains with recording wrappers.

    Call this BEFORE constructing any GameEngine in the training run so
    monsters pick up the wrapped brains when they spawn.  Safe to call
    again with a new logger mid-run; existing species get re-wrapped.
    """
    from game.brain import BrainRegistry, JackalBrain, RatBrain
    from game.monster import get_species_registry

    brain_classes: dict[str, type[Brain]] = {
        "jackal": JackalBrain,
        "rat": RatBrain,
    }
    if species_names is None:
        species_names = list(brain_classes.keys())

    for name in species_names:
        cls_ = brain_classes[name]
        # Load the tabular brain (cached if already present).
        inner = BrainRegistry.get(name, cls_)
        # Unwrap any existing RecordingBrain so we re-wrap the real inner.
        if isinstance(inner, RecordingBrain):
            inner = inner.inner
        wrapped = RecordingBrain(inner, name, logger)
        BrainRegistry._brains[name] = wrapped
        # Reset species caches so the wrapped instance is seen on next access.
        species = get_species_registry().get(name)
        if species is not None:
            species._brain = None


class PolicyBrain(Brain):
    """ONNX-powered Q-network brain.

    Constructed per species.  Uses the species' tabular brain for
    sensory processing so perception stays canonical, and an ONNX
    session for action scoring.  If no model file exists for a
    species, the brain falls back to the embedded tabular brain —
    the game never silently gets a blank policy.
    """

    def __init__(self, species_name: str, model_path: Optional[str] = None,
                 trajectory_logger: Optional[TrajectoryLogger] = None,
                 exploration_rate: float = EXPLORATION_MIN) -> None:
        self.species_name: str = species_name
        self.extractor: FeatureExtractor = get_extractor(species_name)
        self._logger: Optional[TrajectoryLogger] = trajectory_logger
        self._epsilon: float = exploration_rate
        # Keep a tabular brain around for perception and fallback.
        if species_name == "jackal":
            self._sensor = JackalBrain()
        elif species_name == "rat":
            self._sensor = RatBrain()
        else:
            raise ValueError(
                f"no tabular sensor known for species {species_name!r}"
            )
        self._session = None
        self._input_name: Optional[str] = None
        self._output_name: Optional[str] = None
        self.model_path: Optional[str] = model_path
        if model_path is not None:
            self._try_load_model(model_path)

    # -- model loading -----------------------------------------------------

    def _try_load_model(self, path: str) -> None:
        """Best-effort ONNX model load.  Falls back silently on failure."""
        import onnxruntime as ort
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            logger.debug("no ONNX model at %s; using tabular fallback", path)
            return
        try:
            providers = ort.get_available_providers()
            # Prefer the platform's neural accelerator when available.
            preferred = [p for p in ("CoreMLExecutionProvider",
                                     "CUDAExecutionProvider",
                                     "DmlExecutionProvider")
                         if p in providers]
            preferred.append("CPUExecutionProvider")
            self._session = ort.InferenceSession(path, providers=preferred)
            self._input_name = self._session.get_inputs()[0].name
            self._output_name = self._session.get_outputs()[0].name
            logger.info("PolicyBrain[%s] loaded %s with providers %s",
                        self.species_name, path, self._session.get_providers())
        except Exception as exc:
            logger.warning("failed to load ONNX model %s: %s", path, exc)
            self._session = None

    @property
    def has_model(self) -> bool:
        return self._session is not None

    # -- brain API ---------------------------------------------------------

    def perceive(self, monster: Monster, engine: GameEngine) -> dict:
        """Delegate perception to the canonical tabular sensor.

        Not part of the Brain ABC, but required by ``RecordingBrain``
        and any other wrapper that needs to extract features from the
        brain's inputs.
        """
        return self._sensor.perceive(monster, engine)

    def choose_action(self, monster: Monster,
                      engine: GameEngine) -> tuple[Action, dict]:
        """Run perception → ONNX inference → masked action selection."""
        perception = self._sensor.perceive(monster, engine)
        monster.last_state_key = self._sensor._state_key(perception)

        features = self.extractor.extract(monster, perception, engine)
        mask = FeatureExtractor.legal_action_mask(monster, engine)

        # Store for later reward attribution and logging.
        monster.last_nn_features = features
        monster.last_nn_mask = mask

        if not mask.any():
            chosen_idx = 0  # WAIT
        elif _random.random() < self._epsilon or self._session is None:
            legal_indices = np.nonzero(mask)[0]
            chosen_idx = int(_random.choice(legal_indices))
        else:
            chosen_idx = int(self._masked_argmax(features, mask))

        monster.last_nn_action_idx = chosen_idx
        action = ACTION_ORDER[chosen_idx]
        return action, {}

    def record_outcome(self, monster: Monster, action: Action,
                       reward: float, engine: GameEngine) -> None:
        """Log the transition for offline training; no online NN update."""
        if self._logger is None:
            return
        if not hasattr(monster, "last_nn_features"):
            return  # Nothing to log — choose_action never ran.

        # Observe s' by perceiving again from the current state.  If
        # the monster is dead, the terminal features are zeros.
        if monster.is_alive:
            next_perception = self._sensor.perceive(monster, engine)
            next_features = self.extractor.extract(
                monster, next_perception, engine
            )
            next_mask = FeatureExtractor.legal_action_mask(monster, engine)
            done = False
        else:
            next_features = np.zeros_like(monster.last_nn_features)
            next_mask = np.zeros(NUM_ACTIONS, dtype=bool)
            done = True

        self._logger.log(
            species=self.species_name,
            features=monster.last_nn_features,
            action_idx=monster.last_nn_action_idx,
            reward=reward,
            next_features=next_features,
            done=done,
            legal_mask=monster.last_nn_mask,
            next_legal_mask=next_mask,
        )

    def save(self, path: str) -> None:
        """ONNX models are saved by the offline trainer, not the brain.

        This is a no-op that exists only to satisfy the Brain ABC.
        """
        pass

    @classmethod
    def load(cls, path: str) -> PolicyBrain:
        """Factory that infers the species from the path stem.

        Expected layout: ``<model_dir>/<species>.onnx``.  The class
        method signature is fixed by the Brain ABC, so species has to
        be extracted from the filename.
        """
        species = os.path.splitext(os.path.basename(path))[0]
        return cls(species_name=species, model_path=path)

    # -- inference helpers -------------------------------------------------

    def _masked_argmax(self, features: np.ndarray,
                       mask: np.ndarray) -> int:
        """Score actions with the ONNX model, return best legal index."""
        assert self._session is not None
        q = self._session.run(
            [self._output_name],
            {self._input_name: features.reshape(1, -1)},
        )[0].reshape(-1)
        q = q.copy()
        q[~mask] = -np.inf
        return int(np.argmax(q))
