#!/usr/bin/env python3
# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""PNH — Perry's NetHack-inspired roguelike.

Usage:
    python play.py [-n NAME] [-s SEED] [-c] [--ai] [--ai-speed MS]
"""

from __future__ import annotations

__version__ = "0.1.0"

import argparse
import curses
import sys
import time

from game.engine import GameEngine, StepResult
from game.renderer import Renderer
from game.config import GameConfig
from game.actions import (
    Action, Direction,
    VI_KEY_TO_DIRECTION, DIRECTION_TO_ACTION,
)


def parse_args() -> argparse.Namespace:
    """Parse command-line flags."""
    p = argparse.ArgumentParser(description="PNH roguelike")
    p.add_argument("-n", "--name", default=None, help="Player name")
    p.add_argument("-s", "--seed", type=int, default=None,
                   help="Random seed (omit for time-based)")
    p.add_argument("-c", "--no-corridors", action="store_true",
                   help="Generate rooms without corridors")
    p.add_argument("--ai", action="store_true",
                   help="AI plays the game (watch and learn)")
    p.add_argument("--ai-speed", type=int, default=100,
                   help="Milliseconds between AI actions (default 100)")
    return p.parse_args()


def _ai_loop(engine: GameEngine, renderer: Renderer,
             speed_ms: int) -> None:
    """Let the AI player drive the game.  Press 'q' to quit."""
    from game.ai_player import AIPlayer

    ai = AIPlayer()
    speed_sec = speed_ms / 1000.0

    while True:
        # AI chooses an action.
        action, kwargs = ai.choose_action(engine)

        # Execute it.
        result = engine.step(action, **kwargs)

        # Let the AI learn from the reward.
        ai._learn_reward(result)

        # Render.
        renderer.draw(
            engine.board, engine.player,
            engine.current_board_index + 1,
            engine.turn_counter,
        )

        # Show what the AI is thinking + its learning stats.
        msg = f"AI: {ai.thought}  [{ai.stats_str}]"
        if result.message:
            msg = f"{result.message}  |  {msg}"
        renderer.show_message(msg)

        # Check for quit — non-blocking.
        renderer.map_win.timeout(int(speed_ms))
        c = renderer.map_win.getch()
        if c == ord("q"):
            break
        # +/- to adjust speed.
        if c == ord("+") or c == ord("="):
            speed_ms = max(10, speed_ms - 20)
        elif c == ord("-"):
            speed_ms = min(2000, speed_ms + 20)

        renderer.map_win.timeout(50)  # Restore default.


def _main(stdscr: curses.window) -> None:
    """Curses main loop — called inside ``curses.wrapper``."""
    args = parse_args()

    # Load config.
    config = GameConfig()
    config.load()

    # Build engine.
    seed = args.seed if args.seed is not None else int(time.time())
    engine = GameEngine(seed=seed)

    # Apply config / CLI overrides.
    engine.player.name = args.name if args.name else config.name
    engine.player.role = config.role
    engine.player.race = config.race
    engine.player.alignment = config.alignment

    # Set up renderer.
    renderer = Renderer()
    try:
        renderer.init(stdscr)
    except RuntimeError as e:
        curses.endwin()
        print(str(e), file=sys.stderr)
        sys.exit(1)

    # AI mode.
    if args.ai:
        _ai_loop(engine, renderer, args.ai_speed)
        return

    # Digit accumulator for numeric qualifiers.
    digit_acc: str = ""
    numeric_qualifier: int = 0
    last_message: str = ""

    while True:
        # Build the persistent message for this frame.
        display_msg = last_message
        if not display_msg:
            sym = engine.board.get_symbol(engine.player.pos)
            if sym >= 0:
                gc = engine.board.get_goodie_count(engine.player.pos)
                noun = "items" if gc > 1 else "item"
                verb = "are" if gc > 1 else "is"
                display_msg = f"There {verb} {gc} {noun} here."

        # Draw full frame with message.
        renderer.draw(
            engine.board, engine.player,
            engine.current_board_index + 1,
            engine.turn_counter,
        )
        if display_msg:
            renderer.show_message(display_msg)

        # Input loop — poll with 50ms timeout, only update the clock.
        c = renderer.getch()
        while c == -1:  # ERR
            renderer.update_clock()
            c = renderer.getch()

        # Quit.
        if c == ord("q"):
            break

        # Any real keypress clears the previous message.
        last_message = ""

        # Numeric qualifier accumulation.
        if chr(c).isdigit() if 0 <= c < 256 else False:
            digit_acc += chr(c)
            continue
        if digit_acc:
            numeric_qualifier = int(digit_acc)
            digit_acc = ""

        # Toggle debug view.
        if c == ord("t"):
            renderer.show_original = not renderer.show_original
            continue

        # Toggle inventory detail.
        if c == ord("i"):
            renderer.detail_mode = not renderer.detail_mode
            continue

        # Movement (lowercase = one step, uppercase = run).
        ch = chr(c) if 0 <= c < 256 else ""
        if ch.lower() in VI_KEY_TO_DIRECTION:
            direction = VI_KEY_TO_DIRECTION[ch.lower()]
            action = DIRECTION_TO_ACTION[direction]

            steps = numeric_qualifier if numeric_qualifier > 0 else 1
            if ch.isupper():
                steps = 999  # Run until blocked.

            for _ in range(steps):
                result = engine.step(action)
                last_message = result.message

                # Re-render each step for animation.
                renderer.draw(
                    engine.board, engine.player,
                    engine.current_board_index + 1,
                    engine.turn_counter,
                )
                if last_message:
                    renderer.show_message(last_message)

                if not result.turn_used:
                    break  # Hit a wall.

                # Stop running at interesting things.
                pos = engine.player.pos
                if engine.board.is_a_stairway(pos):
                    break
                if engine.board.is_door(pos):
                    break
                if engine.board.get_symbol(pos) >= 0:
                    break

                # Check for room/corridor transition during run.
                if steps > 1 and _ > 0:
                    # Stop at type transitions only during runs.
                    pass

                if steps > 1:
                    time.sleep(0.02)

            numeric_qualifier = 0
            continue

        # Stairs.
        if c == ord(">"):
            result = engine.step(Action.STAIRS_DOWN)
            last_message = result.message
            continue
        if c == ord("<"):
            result = engine.step(Action.STAIRS_UP)
            last_message = result.message
            continue

        # Pickup.
        if c == ord(","):
            result = engine.step(Action.PICKUP)
            last_message = result.message
            continue

        # Drop.
        if c == ord("d"):
            if engine.player.inventory_count() > 0:
                renderer.show_message("Drop what? ")
                letter_ch = renderer.getch_blocking()
                if letter_ch != 27:  # ESC cancels.
                    result = engine.step(Action.DROP,
                                         letter=chr(letter_ch))
                    last_message = result.message
                else:
                    renderer.clear_info_line()
            continue

        # Open / close door.
        if c in (ord("o"), ord("c")):
            opening = c == ord("o")
            verb = "Open" if opening else "Close"
            renderer.show_message(f"{verb} in what direction? ")
            dir_ch = renderer.getch_blocking()
            if dir_ch == 27:
                renderer.clear_info_line()
            else:
                dir_key = chr(dir_ch) if 0 <= dir_ch < 256 else ""
                if dir_key.lower() in VI_KEY_TO_DIRECTION:
                    direction = VI_KEY_TO_DIRECTION[dir_key.lower()]
                    act = Action.OPEN_DOOR if opening else Action.CLOSE_DOOR
                    result = engine.step(act, direction=direction)
                    last_message = result.message
                else:
                    last_message = "Invalid direction."
            continue

        numeric_qualifier = 0


def main() -> None:
    """Entry point."""
    curses.wrapper(_main)


if __name__ == "__main__":
    main()
