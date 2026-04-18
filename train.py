#!/usr/bin/env python3
# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""Headless training runner for PNH.

Drives the AIPlayer through many games so the monster species brains
(jackal, rat) accumulate experience, while the AI's own per-level
world models improve within each game.

Usage:
    python train.py [--turns N] [--per-game-cap N] [--save-every N]
"""

from __future__ import annotations

__version__ = "0.1.0"

import argparse
import sys
import time

from game.brain import BrainRegistry
from game.engine import GameEngine


def _format_brain_stats(player_brain) -> str:
    """Summarize accumulated experience across all learning agents."""
    parts: list[str] = []
    for name, brain in BrainRegistry._brains.items():
        exp = getattr(brain, "total_experiences", 0)
        eps = getattr(brain, "exploration_rate", None)
        if eps is not None:
            parts.append(f"{name}:exp={exp} eps={eps:.2f}")
        else:
            parts.append(f"{name}:exp={exp}")
    parts.append(
        f"ai:act={player_brain.total_actions} "
        f"games={player_brain.games_played} "
        f"deaths={player_brain.deaths} "
        f"items={player_brain.items_collected} "
        f"trans={len(player_brain.transition_counts)}"
    )
    return " ".join(parts)


def train(total_turns: int, per_game_cap: int,
          save_every: int, seed: int) -> None:
    """Run training games until *total_turns* player actions have elapsed."""
    from game.ai_player import AIPlayer, PlayerBrain, AI_BRAIN_PATH

    BrainRegistry.init()
    player_brain = PlayerBrain.load(AI_BRAIN_PATH)

    turns_done: int = 0
    games_done: int = 0
    deaths: int = 0
    turns_since_save: int = 0
    start: float = time.time()
    next_seed: int = seed

    while turns_done < total_turns:
        engine = GameEngine(seed=next_seed)
        next_seed += 1
        ai = AIPlayer(brain=player_brain)
        game_turns: int = 0

        while game_turns < per_game_cap:
            action, kwargs = ai.choose_action(engine)
            result = engine.step(action, **kwargs)
            ai._learn_reward(result)
            game_turns += 1
            turns_done += 1
            turns_since_save += 1

            if result.done:
                deaths += 1
                player_brain.deaths += 1
                break
            if turns_done >= total_turns:
                break

        games_done += 1
        player_brain.games_played += 1

        if turns_since_save >= save_every:
            BrainRegistry.save_all()
            player_brain.save(AI_BRAIN_PATH)
            turns_since_save = 0
            elapsed: float = time.time() - start
            rate: float = turns_done / elapsed if elapsed > 0 else 0.0
            remaining: float = max(0.0, total_turns - turns_done)
            eta: float = remaining / rate if rate > 0 else 0.0
            print(
                f"[{turns_done:>7}/{total_turns}] "
                f"games={games_done} deaths={deaths} "
                f"last_game={game_turns}t "
                f"rate={rate:>5.0f}/s eta={eta:>5.0f}s  "
                f"{_format_brain_stats(player_brain)}",
                flush=True,
            )

    # Final save.
    BrainRegistry.save_all()
    player_brain.save(AI_BRAIN_PATH)
    elapsed = time.time() - start
    print(
        f"\nDone. {turns_done} turns in {elapsed:.1f}s "
        f"({games_done} games, {deaths} deaths, "
        f"{turns_done / max(elapsed, 0.001):.0f} turns/sec).",
        flush=True,
    )
    print(f"Brains: {_format_brain_stats(player_brain)}", flush=True)


def main() -> None:
    p = argparse.ArgumentParser(description="PNH headless trainer")
    p.add_argument("--turns", type=int, default=300_000,
                   help="Total player actions to execute (default 300000)")
    p.add_argument("--per-game-cap", type=int, default=3000,
                   help="Max turns per game before restart (default 3000)")
    p.add_argument("--save-every", type=int, default=10_000,
                   help="Save brains every N turns (default 10000)")
    p.add_argument("--seed", type=int, default=1,
                   help="Starting RNG seed; incremented per game")
    args = p.parse_args()
    train(args.turns, args.per_game_cap, args.save_every, args.seed)


if __name__ == "__main__":
    main()
