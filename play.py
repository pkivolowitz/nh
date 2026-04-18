#!/usr/bin/env python3
# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""PNH -- Perry's NetHack-inspired roguelike.

Usage:
    python play.py [-n NAME] [-s SEED] [-c] [--ai] [--ai-speed MS]
"""

from __future__ import annotations

__version__ = "0.2.0"

import argparse
import curses
import sys
import time

from game.engine import GameEngine, StepResult
from game.renderer import Renderer
from game.config import GameConfig
from game.brain import BrainRegistry
from game.constants import DEFAULT_TORCH_RADIUS
from game.actions import (
    Action, Direction,
    VI_KEY_TO_DIRECTION, DIRECTION_TO_ACTION,
)
from game.magic import SCHOOL_HOTKEYS, SCHOOL_NAMES, MagicSchool, ProficiencyTier
from game.spells_fire import (
    TIER_HAS_CURSOR, TIER_RADIUS_CHOICES, RADIUS_NAMES,
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
    p.add_argument("--brain-mode", choices=["tabular", "nn"], default=None,
                   help="Monster brain mode; overrides PNH_BRAIN_MODE env var")
    p.add_argument("--ai-mode", choices=["rule", "nn"], default="rule",
                   help="AI player brain: rule-based planner or ONNX policy")
    return p.parse_args()


def _ai_loop(engine: GameEngine, renderer: Renderer,
             speed_ms: int, ai_mode: str = "rule") -> None:
    """Let the AI player drive the game.  Press 'q' to quit.

    *ai_mode* is ``"rule"`` (default rule-based planner with persistent
    PlayerBrain) or ``"nn"`` (ONNX dueling policy).  Loads persistent
    state on entry and saves it on exit so interactive watch sessions
    contribute to long-term learning.
    """
    from game.ai_player import (
        AIPlayer, PolicyAIPlayer, PlayerBrain, AI_BRAIN_PATH,
    )

    brain = PlayerBrain.load(AI_BRAIN_PATH)
    if ai_mode == "nn":
        ai = PolicyAIPlayer(brain=brain)
        if not ai.has_model:
            renderer.show_message(
                "No ONNX player model found — falling back to random actions."
            )
    else:
        ai = AIPlayer(brain=brain)
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

        # Show what the AI is thinking.  Truncate to one line so the
        # renderer does not open a blocking "--More--" pager between
        # every turn.
        from game.constants import BOARD_COLUMNS
        msg = f"AI: {ai.thought}"
        if result.message:
            msg = f"{result.message}  |  {msg}"
        if len(msg) >= BOARD_COLUMNS:
            msg = msg[:BOARD_COLUMNS - 2] + "…"
        renderer.show_message(msg)

        # Player died.
        if result.done:
            brain.deaths += 1
            renderer.show_message("AI died! Press any key to exit.")
            renderer.getch_blocking()
            break

        # Check for quit -- non-blocking.
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

    brain.games_played += 1
    brain.save(AI_BRAIN_PATH)


def _monster_visible(engine: GameEngine) -> bool:
    """True if any monster is visible to the player right now."""
    pos = engine.player.pos
    for m in engine.board.get_all_monsters():
        if (m.pos.distance(pos) < DEFAULT_TORCH_RADIUS
                and engine.board.line_of_sight(pos, m.pos)):
            return True
    return False


def _main(stdscr: curses.window) -> None:
    """Curses main loop -- called inside ``curses.wrapper``."""
    args = parse_args()

    # Configure monster brain mode before any engine construction so
    # species pick up the right brain type on first spawn.
    BrainRegistry.init(mode=args.brain_mode)

    # Load config.
    config = GameConfig()
    config.load()

    # Try to restore a saved game; fall back to a fresh one.
    engine: GameEngine | None = GameEngine.load()
    if engine is None:
        seed = args.seed if args.seed is not None else int(time.time())
        engine = GameEngine(seed=seed)
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
        _ai_loop(engine, renderer, args.ai_speed, ai_mode=args.ai_mode)
        BrainRegistry.save_all()
        return

    # Digit accumulator for numeric qualifiers.
    digit_acc: str = ""
    numeric_qualifier: int = 0
    last_message: str = ""

    while True:
        # Check for game over (player may have died last turn).
        if not engine.player.is_alive:
            renderer.draw(
                engine.board, engine.player,
                engine.current_board_index + 1,
                engine.turn_counter,
            )
            renderer.show_message(last_message or "You died!")
            renderer.getch_blocking()
            break

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

        # Input loop -- poll with 50ms timeout, only update the clock.
        c = renderer.getch()
        while c == -1:  # ERR
            renderer.update_clock()
            c = renderer.getch()

        # Quit.
        if c == ord("q"):
            break

        # Freeze — save state and exit immediately so the player
        # can come back to this exact moment and report what they see.
        if c == 19:  # Ctrl+S
            BrainRegistry.save_all()
            engine.save()
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

        # Help.
        if c == ord("?") or c == 127:
            renderer.show_help()
            continue

        # Toggle debug view.
        if c == ord("t"):
            renderer.show_original = not renderer.show_original
            continue

        # Toggle inventory detail.
        if c == ord("i"):
            renderer.detail_mode = not renderer.detail_mode
            continue

        # Wizard mode: set school proficiency for testing.
        if c == ord("W"):
            from game.magic import TIER_THRESHOLDS
            school_opts: list[str] = [
                f"{hk}={SCHOOL_NAMES[sc]}"
                for hk, sc in SCHOOL_HOTKEYS.items()
            ]
            renderer.show_message(
                "[WIZARD] School? [" + ", ".join(school_opts) + "] "
            )
            wch = renderer.getch_blocking()
            if wch == 27:
                renderer.clear_info_line()
                continue
            wkey = chr(wch).lower() if 0 <= wch < 256 else ""
            if wkey not in SCHOOL_HOTKEYS:
                last_message = "Invalid school."
                continue
            wschool = SCHOOL_HOTKEYS[wkey]
            tier_opts: list[str] = [
                f"{t.value}={t.name.lower()}"
                for t in ProficiencyTier
            ]
            renderer.show_message(
                f"[WIZARD] {SCHOOL_NAMES[wschool]} tier? ["
                + ", ".join(tier_opts) + "] "
            )
            tch = renderer.getch_blocking()
            if tch == 27:
                renderer.clear_info_line()
                continue
            tidx = tch - ord("0")
            try:
                chosen_tier = ProficiencyTier(tidx)
            except ValueError:
                last_message = "Invalid tier."
                continue
            ws = engine.player.magic.schools[wschool]
            ws.known = True
            ws.xp = TIER_THRESHOLDS[chosen_tier]
            last_message = (
                f"[WIZARD] {SCHOOL_NAMES[wschool]} set to "
                f"{chosen_tier.name.lower()}."
            )
            continue

        # Movement (lowercase = one step, uppercase = run).
        ch = chr(c) if 0 <= c < 256 else ""
        if ch.lower() in VI_KEY_TO_DIRECTION:
            direction = VI_KEY_TO_DIRECTION[ch.lower()]
            action = DIRECTION_TO_ACTION[direction]

            steps = numeric_qualifier if numeric_qualifier > 0 else 1
            running: bool = ch.isupper()
            if running:
                steps = 999  # Run until blocked.

            for _ in range(steps):
                result = engine.step(action, running=running)
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

                # Stop running on death.
                if result.done:
                    break

                # Stop running at interesting things.
                pos = engine.player.pos
                if engine.board.is_a_stairway(pos):
                    break
                if engine.board.is_door(pos):
                    break
                if engine.board.get_symbol(pos) >= 0:
                    break

                # Stop running if a monster is visible.
                if _monster_visible(engine):
                    break

                # Check for room/corridor transition during run.
                if steps > 1 and _ > 0:
                    # Stop at type transitions only during runs.
                    pass

                if steps > 1:
                    time.sleep(0.02)

            numeric_qualifier = 0
            continue

        # Rest in place — world advances one turn (NetHack '.').
        if c == ord("."):
            result = engine.step(Action.WAIT)
            last_message = result.message
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

        # Kick (Ctrl+K).
        if c == 11:
            renderer.show_message("Kick in what direction? ")
            dir_ch = renderer.getch_blocking()
            if dir_ch == 27:
                renderer.clear_info_line()
            else:
                dir_key = chr(dir_ch) if 0 <= dir_ch < 256 else ""
                if dir_key.lower() in VI_KEY_TO_DIRECTION:
                    direction = VI_KEY_TO_DIRECTION[dir_key.lower()]
                    result = engine.step(Action.KICK_DOOR,
                                         direction=direction)
                    last_message = result.message
                else:
                    last_message = "Invalid direction."
            continue

        # Cast spell (z).
        if c == ord("z"):
            known = engine.player.magic.known_schools()
            if not known:
                last_message = "You don't know any magic."
                continue
            # Build the school selection prompt.
            opts: list[str] = []
            for hotkey, school_enum in SCHOOL_HOTKEYS.items():
                if school_enum in known:
                    opts.append(f"{hotkey}={SCHOOL_NAMES[school_enum]}")
            prompt: str = "Cast which school? [" + ", ".join(opts) + "] "
            renderer.show_message(prompt)
            sch_ch = renderer.getch_blocking()
            if sch_ch == 27:
                renderer.clear_info_line()
                continue
            sch_key = chr(sch_ch).lower() if 0 <= sch_ch < 256 else ""
            if sch_key not in SCHOOL_HOTKEYS or SCHOOL_HOTKEYS[sch_key] not in known:
                last_message = "You don't know that school."
                continue
            chosen_school: MagicSchool = SCHOOL_HOTKEYS[sch_key]
            school_state = engine.player.magic.schools[chosen_school]
            tier: ProficiencyTier = school_state.tier

            # Targeting: cursor for apprentice+, direction for novice.
            target_pos = None
            direction = Direction.NONE
            if TIER_HAS_CURSOR.get(tier, False):
                renderer.show_message(
                    f"Select target for {SCHOOL_NAMES[chosen_school]}. "
                    f"Move cursor, '.' to confirm, ESC to cancel."
                )
                target_pos = renderer.select_target(
                    engine.board, engine.player.pos
                )
                if target_pos is None:
                    renderer.clear_info_line()
                    continue
            else:
                renderer.show_message(
                    f"Cast {SCHOOL_NAMES[chosen_school]} in what direction? "
                )
                dir_ch = renderer.getch_blocking()
                if dir_ch == 27:
                    renderer.clear_info_line()
                    continue
                dir_key = chr(dir_ch) if 0 <= dir_ch < 256 else ""
                if dir_key.lower() in VI_KEY_TO_DIRECTION:
                    direction = VI_KEY_TO_DIRECTION[dir_key.lower()]
                else:
                    direction = Direction.NONE

            # Radius selection: only if tier offers choices.
            spell_radius: int = -1
            radius_choices = TIER_RADIUS_CHOICES.get(tier, [])
            if radius_choices:
                opts_r: list[str] = [
                    f"{i+1}={RADIUS_NAMES[r]}"
                    for i, r in enumerate(radius_choices)
                ]
                renderer.show_message(
                    "Blast size? [" + ", ".join(opts_r) + "] "
                )
                rad_ch = renderer.getch_blocking()
                if rad_ch == 27:
                    renderer.clear_info_line()
                    continue
                rad_idx = rad_ch - ord("1")
                if 0 <= rad_idx < len(radius_choices):
                    spell_radius = radius_choices[rad_idx]
                else:
                    last_message = "Invalid choice."
                    continue

            # Redraw before resolving so the cursor is cleaned up.
            renderer.draw(
                engine.board, engine.player,
                engine.current_board_index + 1,
                engine.turn_counter,
            )

            result = engine.step(
                Action.CAST,
                school=chosen_school,
                direction=direction,
                target_pos=target_pos,
                spell_radius=spell_radius,
            )
            last_message = result.message
            continue

        # Read (r) — read a spellbook from inventory.
        if c == ord("r"):
            if engine.player.inventory_count() == 0:
                last_message = "You have nothing to read."
                continue
            renderer.show_message("Read which item? ")
            letter_ch = renderer.getch_blocking()
            if letter_ch == 27:
                renderer.clear_info_line()
            else:
                result = engine.step(Action.READ,
                                     letter=chr(letter_ch))
                last_message = result.message
            continue

        numeric_qualifier = 0

    # Persist all brain state learned during this session.
    BrainRegistry.save_all()

    # Save game on quit; delete save on death (permadeath).
    if engine.player.is_alive:
        engine.save()
    else:
        GameEngine.delete_save()


def main() -> None:
    """Entry point."""
    curses.wrapper(_main)


if __name__ == "__main__":
    main()
