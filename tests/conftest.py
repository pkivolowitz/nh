# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""Shared test fixtures.

Every test runs with isolated save directories, brain directories, and
species registries so there is no cross-test contamination and no risk
of stomping on the user's real ~/.pnh files.
"""

from __future__ import annotations

import os
import shutil

import pytest

from game.engine import GameEngine
from game.brain import BrainRegistry


@pytest.fixture
def tmp_pnh_dir(tmp_path, monkeypatch):
    """Isolate all PNH state under *tmp_path* for the duration of one test.

    Redirects the engine's save directory and the brain registry's
    persistence directory into a clean temp directory, so nothing the
    test writes touches the user's real dotfiles.
    """
    save_dir: str = str(tmp_path / "pnh")
    os.makedirs(save_dir, exist_ok=True)
    monkeypatch.setattr(GameEngine, "SAVE_DIR", save_dir)

    brain_dir: str = str(tmp_path / "brains")
    os.makedirs(brain_dir, exist_ok=True)
    # Reset registry state so previous tests' brains don't leak.
    BrainRegistry._brains = {}
    BrainRegistry._mode = "tabular"
    BrainRegistry.init(brain_dir=brain_dir, mode="tabular",
                       model_dir=str(tmp_path / "models"))
    # Clear cached brain references on species so a stale instance
    # (e.g. a PolicyBrain from a prior test) doesn't survive.
    from game.monster import get_species_registry
    for species in get_species_registry().values():
        species._brain = None
    yield tmp_path
    BrainRegistry._brains = {}
    BrainRegistry._mode = "tabular"
    for species in get_species_registry().values():
        species._brain = None


@pytest.fixture
def fresh_engine(tmp_pnh_dir) -> GameEngine:
    """A deterministic engine seeded so tests are reproducible."""
    return GameEngine(seed=12345)
