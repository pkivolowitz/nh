#!/usr/bin/env python3
# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""A/B comparison: tabular-brain monsters vs NN-brain monsters.

Runs matched pairs of headless games with identical seeds and reports
aggregate metrics.  Intended to answer: does the trained ONNX policy
produce more lethal / longer-lived / more active monsters than the
tabular baseline?

Metrics tracked per arm:
    games played, player deaths, total player turns (longevity proxy),
    monster kills dealt to the player per game, monster kills taken
    by monsters per game, player final HP per game.

Usage:
    python ab_compare.py [--games 20] [--per-game-cap 2000] [--seed-base 1000]
"""

from __future__ import annotations

__version__ = "0.1.0"

import argparse
import statistics
import time
from dataclasses import dataclass, field


@dataclass
class ArmStats:
    name: str
    games: int = 0
    deaths: int = 0
    turns_total: int = 0
    monster_kills_taken: int = 0  # Monsters that died during games.
    player_kills_landed: int = 0  # Hits the player dealt.
    final_hps: list[int] = field(default_factory=list)
    turns_per_game: list[int] = field(default_factory=list)

    def summary(self) -> str:
        def mean(xs):
            return statistics.mean(xs) if xs else 0.0
        def median(xs):
            return statistics.median(xs) if xs else 0.0
        return (
            f"{self.name:<8} | games={self.games} deaths={self.deaths} "
            f"({100 * self.deaths / max(1, self.games):5.1f}%) "
            f"turns_total={self.turns_total} "
            f"turns/game mean={mean(self.turns_per_game):6.0f} "
            f"median={median(self.turns_per_game):6.0f} "
            f"monster_kills={self.monster_kills_taken} "
            f"final_hp mean={mean(self.final_hps):4.1f}"
        )


def run_arm(mode: str, *, games: int, per_game_cap: int,
            seed_base: int) -> ArmStats:
    """Run *games* trials in the given brain mode and aggregate metrics."""
    # Local imports so the arm can cleanly reset BrainRegistry between arms.
    from game.brain import BrainRegistry
    from game.engine import GameEngine
    from game.ai_player import AIPlayer, PlayerBrain

    # Reset registry so previous-mode instances don't leak in.
    BrainRegistry._brains = {}
    BrainRegistry.init(mode=mode)

    stats = ArmStats(name=mode)
    for game_i in range(games):
        engine = GameEngine(seed=seed_base + game_i)
        ai = AIPlayer(brain=PlayerBrain())  # Fresh brain per arm, no contamination.

        initial_monster_count: int = sum(
            len(b.get_all_monsters()) for b in engine.boards
        )
        game_turns: int = 0
        while game_turns < per_game_cap:
            action, kwargs = ai.choose_action(engine)
            result = engine.step(action, **kwargs)
            ai._learn_reward(result)
            game_turns += 1
            if result.done:
                stats.deaths += 1
                break

        stats.games += 1
        stats.turns_total += game_turns
        stats.turns_per_game.append(game_turns)
        stats.final_hps.append(engine.player.hp)

        remaining_monsters: int = sum(
            len(b.get_all_monsters()) for b in engine.boards
        )
        stats.monster_kills_taken += max(
            0, initial_monster_count - remaining_monsters,
        )

    return stats


def main() -> None:
    p = argparse.ArgumentParser(description="A/B compare tabular vs NN brains")
    p.add_argument("--games", type=int, default=20)
    p.add_argument("--per-game-cap", type=int, default=2000)
    p.add_argument("--seed-base", type=int, default=1000)
    args = p.parse_args()

    print(f"A/B compare: {args.games} games per arm, cap={args.per_game_cap}, "
          f"seed_base={args.seed_base}\n")

    t0 = time.time()
    tab = run_arm("tabular", games=args.games,
                  per_game_cap=args.per_game_cap, seed_base=args.seed_base)
    t1 = time.time()
    print(f"tabular arm: {t1 - t0:.1f}s")

    nn = run_arm("nn", games=args.games,
                 per_game_cap=args.per_game_cap, seed_base=args.seed_base)
    t2 = time.time()
    print(f"nn arm:      {t2 - t1:.1f}s\n")

    print(tab.summary())
    print(nn.summary())
    print()

    # Quick qualitative readouts.
    def mean(xs):
        return statistics.mean(xs) if xs else 0.0

    delta_hp = mean(tab.final_hps) - mean(nn.final_hps)
    delta_turns = mean(tab.turns_per_game) - mean(nn.turns_per_game)
    delta_deaths = tab.deaths - nn.deaths
    print("Δ (tabular − nn):")
    print(f"  player_final_hp: {delta_hp:+.2f}   "
          f"(NN brains more dangerous if negative)")
    print(f"  turns_per_game:  {delta_turns:+.1f}  "
          f"(NN brains end games faster if positive)")
    print(f"  player_deaths:   {delta_deaths:+d}   "
          f"(NN brains deadlier if negative)")


if __name__ == "__main__":
    main()
