# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""Game engine: turn processing, action execution, and the ML step() interface.

The engine owns the authoritative game state and has *no* curses
dependency.  It can run headless for batch ML training or be driven
interactively through the renderer.

Combat is resolved when a creature bumps into another.  Monster turns
run after every player action via a speed-based energy system.
"""

from __future__ import annotations

__version__ = "0.2.0"

import os
import pickle
import random
from typing import Optional

from game.constants import (
    BOARD_COLUMNS,
    BOARD_ROWS,
    DEFAULT_TORCH_RADIUS,
    ENERGY_THRESHOLD,
    UNARMED_DICE,
    UNARMED_SIDES,
    UNARMED_VERBS,
    UNARMED_KILL_VERBS,
    NOISE_WALK,
    NOISE_RUN,
    NOISE_DROP,
    NOISE_KICK,
    NOISE_MELEE,
    HEAL_BASE_INTERVAL,
    HEAL_CON_SCALE,
    KICK_NOTHING_HURT_CHANCE,
    KICK_NOTHING_DICE,
    KICK_NOTHING_SIDES,
)
from game.cell import CellBaseType, DoorState
from game.coordinate import Coordinate
from game.board import Board
from game.player import Player, Trait
from game.magic import (
    MagicSchool, SchoolState, CastResult, CastOutcome,
    SCHOOL_NAMES, SCHOOL_CAST_VERBS, LOW_CONC_MESSAGES,
    CONC_BASE_INTERVAL, CONC_INT_SCALE,
    roll_outcome,
)
from game.actions import (
    Action, Direction, DIRECTION_DELTA, ACTION_TO_DIRECTION,
)
from game.drawing_support import initialize_corner_map
from game.combat import BumpAttack, CombatResult
from game.brain import (
    BrainRegistry,
    REWARD_DEATH,
    REWARD_DEAL_DAMAGE_SCALE,
    REWARD_MOVE_TOWARD_PREY,
    REWARD_MOVE_AWAY_PREY,
    REWARD_FAILED_MOVE,
    REWARD_WAIT,
)
from game.monster import Monster

# Player's unarmed melee attack (placeholder until weapons exist).
_PLAYER_UNARMED: BumpAttack = BumpAttack(
    dice=UNARMED_DICE, sides=UNARMED_SIDES, verb="hit"
)


class StepResult:
    """Return value of ``GameEngine.step``."""

    __slots__ = ("message", "reward", "done", "turn_used")

    def __init__(self, message: str = "", reward: float = 0.0,
                 done: bool = False, turn_used: bool = False) -> None:
        self.message: str = message
        self.reward: float = reward
        self.done: bool = done
        self.turn_used: bool = turn_used


class GameEngine:
    """Pure-logic game engine.

    Public interface
    ----------------
    step(action, **kwargs) -> StepResult
        Execute one discrete action and advance game state.
    get_observation() -> dict
        Machine-readable snapshot for agents.
    """

    def __init__(self, seed: Optional[int] = None) -> None:
        self.rng: random.Random = random.Random(seed)
        initialize_corner_map()
        BrainRegistry.init()

        self.boards: list[Board] = []
        self.current_board_index: int = 0
        self.turn_counter: int = 0
        self.player: Player = Player(self.rng)
        self._monsters_placed: set[int] = set()
        self._last_heal_turn: int = 0
        self._last_conc_turn: int = 0

        # Generate the first level.
        self._new_board()
        self.player.pos = Coordinate(
            self.board.upstairs.r, self.board.upstairs.c
        )
        # Place monsters (never in the player's starting room).
        self.board.place_monsters(self.player.pos, 1)
        self._monsters_placed.add(0)

        # Mark the player's initial surroundings as known.
        self.board.update_visibility(self.player.pos)

    @property
    def board(self) -> Board:
        """The currently active dungeon level."""
        return self.boards[self.current_board_index]

    # ------------------------------------------------------------------
    # Action dispatch
    # ------------------------------------------------------------------

    def step(self, action: Action, *,
             direction: Direction = Direction.NONE,
             letter: str = "",
             running: bool = False,
             school: Optional[MagicSchool] = None,
             target_pos: Optional[Coordinate] = None,
             spell_radius: int = -1) -> StepResult:
        """Execute *action* and return the result.

        After the player acts, all monsters on the level accumulate
        energy and take their turns if energy >= threshold.

        ``running`` is True when the player is in a run (uppercase
        vi-key movement); it selects the louder NOISE_RUN emission.
        ``school`` is required for CAST actions.
        """
        # Clear stale noise from the previous step — every turn
        # starts with a clean noise slate.
        self.board.clear_noise()

        if action == Action.WAIT:
            self.turn_counter += 1
            result = StepResult(turn_used=True)
        elif action in ACTION_TO_DIRECTION:
            result = self._handle_move(
                ACTION_TO_DIRECTION[action], running=running
            )
        elif action == Action.STAIRS_DOWN:
            result = self._handle_stairs_down()
        elif action == Action.STAIRS_UP:
            result = self._handle_stairs_up()
        elif action == Action.PICKUP:
            result = self._handle_pickup()
        elif action == Action.DROP:
            result = self._handle_drop(letter)
        elif action == Action.OPEN_DOOR:
            result = self._handle_door(direction, opening=True)
        elif action == Action.CLOSE_DOOR:
            result = self._handle_door(direction, opening=False)
        elif action == Action.KICK_DOOR:
            result = self._handle_kick(direction)
        elif action == Action.CAST:
            result = self._handle_cast(school, direction,
                                       target_pos=target_pos,
                                       spell_radius=spell_radius)
        elif action == Action.READ:
            result = self._handle_read(letter)
        else:
            result = StepResult(message="Unknown action.")

        # Run monster turns after every player action that used a turn.
        if result.turn_used and self.player.is_alive:
            monster_msgs: list[str] = self._run_monster_turns()
            if monster_msgs:
                combined: str = result.message
                for mm in monster_msgs:
                    if combined:
                        combined += " "
                    combined += mm
                result.message = combined

        # Tick ephemeral tile effects (fire burns, scorch fades).
        if result.turn_used:
            effect_msgs: list[str] = self.board.tick_effects()
            for em in effect_msgs:
                if result.message:
                    result.message += " " + em
                else:
                    result.message = em
            # Player standing in fire takes damage.
            if self.player.is_alive:
                from game.effects import EffectType
                player_effect = self.board.get_effect_at(self.player.pos)
                if (player_effect is not None
                        and player_effect.effect_type == EffectType.FIRE
                        and player_effect.damage_per_turn > 0):
                    self.player.take_damage(player_effect.damage_per_turn)
                    fire_msg: str = "The flames sear your flesh!"
                    if result.message:
                        result.message += " " + fire_msg
                    else:
                        result.message = fire_msg

        # Build hear messages for any monster noises the player can
        # perceive but not see directly.
        if self.player.is_alive:
            hear_msgs: list[str] = self.board.get_player_hear_messages(
                self.player.pos, DEFAULT_TORCH_RADIUS
            )
            for hm in hear_msgs:
                if result.message:
                    result.message += " " + hm
                else:
                    result.message = hm

        # Natural healing and concentration regen — slow recovery each turn.
        if result.turn_used and self.player.is_alive:
            self._try_natural_heal()
            self._try_conc_regen()

        # Check for player death (monsters may have killed the player).
        if not self.player.is_alive:
            result.done = True
            if "die" not in result.message.lower():
                result.message += " You die..."

        # Update visibility from the player's new position so both
        # the renderer and headless agents see consistent is_known.
        self.board.update_visibility(self.player.pos)
        return result

    # ------------------------------------------------------------------
    # Movement
    # ------------------------------------------------------------------

    def _handle_move(self, direction: Direction, *,
                     running: bool = False) -> StepResult:
        """Move the player one step in *direction*.

        Emits walking or running noise on a successful step.  Bumping
        into a monster triggers melee combat instead.
        """
        dr, dc = DIRECTION_DELTA[direction]
        target = Coordinate(self.player.pos.r + dr, self.player.pos.c + dc)

        # Bounds check — silently stop at map edges.
        if not (0 <= target.r < BOARD_ROWS and 0 <= target.c < BOARD_COLUMNS):
            return StepResult()

        # Monster at target -- bump to attack.
        monster: Optional[Monster] = self.board.get_monster_at(target)
        if monster:
            return self._player_attacks_monster(monster)

        # Terrain collision check.
        if not self.board.is_navigable(target):
            if self.board.is_door(target):
                cell = self.board.cells[target.r][target.c]
                msgs = {
                    DoorState.DOOR_CLOSED: "The door is closed.",
                    DoorState.DOOR_LOCKED: "This door is locked.",
                    DoorState.DOOR_STUCK: "The door is stuck!",
                }
                return StepResult(message=msgs.get(cell.door_state, ""))
            return StepResult()

        self.player.pos = target
        self.turn_counter += 1

        # Emit footstep noise from the new position.
        noise_level: int = NOISE_RUN if running else NOISE_WALK
        self.board.emit_noise(self.player.pos, noise_level)

        # Report items on the floor by name.
        msg = ""
        items_here = self.board.goodies.get(target, [])
        if items_here:
            descs = [it.describe() for it in items_here]
            if len(descs) == 1:
                msg = f"You see here {descs[0]}."
            else:
                msg = "You see here: " + ", ".join(descs) + "."

        return StepResult(message=msg, turn_used=True)

    # ------------------------------------------------------------------
    # Combat
    # ------------------------------------------------------------------

    def _player_attacks_monster(self, monster: Monster) -> StepResult:
        """Player bumps into a monster -- resolve melee combat.

        Picks a random unarmed verb from UNARMED_VERBS to keep the
        prose varied.  Killing blows use UNARMED_KILL_VERBS.  Melee
        combat is loud and emits noise from the player's position.
        """
        result: CombatResult = _PLAYER_UNARMED.execute(
            self.player, monster, self.rng,
            damage_bonus=self.player.melee_damage_bonus(),
        )
        self.turn_counter += 1
        self.board.emit_noise(self.player.pos, NOISE_MELEE)

        reward: float = 0.5
        if result.defender_killed:
            # Record death in the species brain before removing.
            brain = monster.species.get_brain()
            if monster.last_action is not None:
                brain.record_outcome(
                    monster, monster.last_action, REWARD_DEATH, self
                )
            self.board.remove_monster(monster.pos)
            kill_verb: str = self.rng.choice(UNARMED_KILL_VERBS)
            msg: str = f"You {kill_verb} the {monster.name}!"
            reward = 2.0
        else:
            verb: str = self.rng.choice(UNARMED_VERBS)
            msg = f"You {verb} the {monster.name}. ({result.damage} damage)"

        return StepResult(message=msg, reward=reward, turn_used=True)

    def _monster_attacks_player(self, monster: Monster,
                                action: Action) -> Optional[str]:
        """A monster bumps into the player -- resolve melee combat."""
        if not monster.species.attacks:
            return None

        attack: BumpAttack = monster.species.attacks[0]
        result: CombatResult = attack.execute(monster, self.player, self.rng)

        # Record damage reward in the species brain.
        brain = monster.species.get_brain()
        reward: float = result.damage * REWARD_DEAL_DAMAGE_SCALE
        brain.record_outcome(monster, action, reward, self)

        if result.defender_killed:
            return f"The {monster.name} {attack.verb} you! You die..."
        return f"The {monster.name} {attack.verb} you! ({result.damage} damage)"

    # ------------------------------------------------------------------
    # Monster turns (speed-based energy system)
    # ------------------------------------------------------------------

    def _run_monster_turns(self) -> list[str]:
        """Accumulate energy and execute monster actions.

        Each monster gains ``speed`` energy per tick.  When energy
        reaches ``ENERGY_THRESHOLD``, the monster acts and energy is
        decremented.  Faster creatures may act multiple times.
        """
        messages: list[str] = []
        # Snapshot the list -- monsters may die during processing.
        monsters: list[Monster] = self.board.get_all_monsters()

        for monster in monsters:
            if not monster.is_alive:
                continue
            if not self.player.is_alive:
                break

            monster.energy += monster.speed
            while (monster.energy >= ENERGY_THRESHOLD
                   and monster.is_alive
                   and self.player.is_alive):
                monster.energy -= ENERGY_THRESHOLD
                msg: Optional[str] = self._execute_monster_turn(monster)
                if msg:
                    messages.append(msg)

        return messages

    def _execute_monster_turn(self, monster: Monster) -> Optional[str]:
        """Execute a single turn for one monster."""
        brain = monster.species.get_brain()
        action, _kwargs = brain.choose_action(monster, self)
        monster.last_action = action

        if action in ACTION_TO_DIRECTION:
            return self._monster_move(monster, action)

        if action == Action.WAIT:
            brain.record_outcome(monster, action, REWARD_WAIT, self)

        return None

    def _monster_move(self, monster: Monster,
                      action: Action) -> Optional[str]:
        """Resolve a monster's movement action (may trigger combat)."""
        direction: Direction = ACTION_TO_DIRECTION[action]
        dr, dc = DIRECTION_DELTA[direction]
        target: Coordinate = Coordinate(
            monster.pos.r + dr, monster.pos.c + dc
        )
        brain = monster.species.get_brain()

        # Bounds check.
        if not (0 <= target.r < BOARD_ROWS
                and 0 <= target.c < BOARD_COLUMNS):
            brain.record_outcome(monster, action, REWARD_FAILED_MOVE, self)
            return None

        # Bumping into the player triggers combat.
        if target == self.player.pos:
            return self._monster_attacks_player(monster, action)

        # Move to navigable, unoccupied cell.
        if (self.board.is_navigable(target)
                and self.board.get_monster_at(target) is None):
            old_dist: float = monster.pos.distance(self.player.pos)
            new_dist: float = target.distance(self.player.pos)

            # Species-appropriate shaping reward.
            from game.brain import RatBrain
            if isinstance(brain, RatBrain):
                reward = self._rat_move_reward(
                    monster, target, old_dist, new_dist
                )
            else:
                # Predator brain (jackal): closing distance is good.
                can_see: bool = self.board.line_of_sight(
                    monster.pos, self.player.pos
                )
                if can_see:
                    reward: float = (REWARD_MOVE_TOWARD_PREY
                                     if new_dist < old_dist
                                     else REWARD_MOVE_AWAY_PREY)
                else:
                    reward = 0.0

            self.board.move_monster(monster, target)

            # Monsters emit noise from their new position.
            self.board.emit_noise(
                monster.pos,
                monster.species.move_noise,
                description=monster.species.noise_description,
                is_monster=True,
            )

            brain.record_outcome(monster, action, reward, self)
            return None

        # Blocked by terrain or another monster.
        brain.record_outcome(monster, action, REWARD_FAILED_MOVE, self)
        return None

    def _rat_move_reward(self, monster: Monster, target: Coordinate,
                         old_dist: float, new_dist: float) -> float:
        """Compute shaping reward for a rat's movement.

        Rats are rewarded for fleeing the player and moving toward
        food.  Getting closer to the player is punished.
        """
        from game.brain import (
            REWARD_RAT_FLEE, REWARD_RAT_APPROACH_PREY,
            REWARD_RAT_FOOD_CLOSER, REWARD_RAT_ON_FOOD,
        )
        from game.items import ItemType

        reward: float = 0.0

        # Flee/approach player.
        if new_dist > old_dist:
            reward += REWARD_RAT_FLEE
        elif new_dist < old_dist:
            reward += REWARD_RAT_APPROACH_PREY

        # Food proximity reward, scoped to the rat's own smell radius.
        smell_r: float = monster.senses.smell_radius()
        best_food_dist_old: float = smell_r + 1
        best_food_dist_new: float = smell_r + 1
        for coord, items in self.board.goodies.items():
            for item in items:
                if item.type == ItemType.FOOD:
                    d_old: float = monster.pos.distance(coord)
                    d_new: float = target.distance(coord)
                    if d_old < best_food_dist_old:
                        best_food_dist_old = d_old
                    if d_new < best_food_dist_new:
                        best_food_dist_new = d_new
                    break

        if best_food_dist_new < best_food_dist_old:
            reward += REWARD_RAT_FOOD_CLOSER
        if best_food_dist_new <= 0.01:
            reward += REWARD_RAT_ON_FOOD

        return reward

    # ------------------------------------------------------------------
    # Stairs
    # ------------------------------------------------------------------

    def _handle_stairs_down(self) -> StepResult:
        if not self.board.is_downstairs(self.player.pos):
            return StepResult(message="You can't go down here.")
        self.turn_counter += 1
        if self.current_board_index == len(self.boards) - 1:
            self._new_board()
        self.current_board_index += 1
        self.player.pos = Coordinate(
            self.board.upstairs.r, self.board.upstairs.c
        )
        # Place monsters on first visit to this level.
        level: int = self.current_board_index
        if level not in self._monsters_placed:
            self.board.place_monsters(
                self.player.pos, level + 1
            )
            self._monsters_placed.add(level)
        return StepResult(message="You descend the staircase.",
                          turn_used=True)

    def _handle_stairs_up(self) -> StepResult:
        if not self.board.is_upstairs(self.player.pos):
            return StepResult(message="You can't go up here.")
        if self.current_board_index == 0:
            return StepResult(message="You are already on the top level.")
        self.turn_counter += 1
        self.current_board_index -= 1
        self.player.pos = Coordinate(
            self.board.downstairs.r, self.board.downstairs.c
        )
        return StepResult(message="You ascend the staircase.",
                          turn_used=True)

    # ------------------------------------------------------------------
    # Items
    # ------------------------------------------------------------------

    def _handle_pickup(self) -> StepResult:
        items = self.board.remove_goodies(self.player.pos)
        if not items:
            return StepResult(message="There is nothing here to pick up.")

        picked_up = 0
        full = False
        too_heavy = False
        reward = 0.0
        max_wt: int = self.player.max_carry_weight()
        for item in items:
            if full or too_heavy:
                self.board.add_goodie(self.player.pos, item)
                continue
            # Check weight before adding.
            if self.player.weight_of_inventory() + item.weight() > max_wt:
                too_heavy = True
                self.board.add_goodie(self.player.pos, item)
                continue
            letter = self.player.add_to_inventory(item)
            if not letter:
                full = True
                self.board.add_goodie(self.player.pos, item)
            else:
                picked_up += 1
                reward += 1.0  # Reward signal for ML agents.

        if picked_up > 0:
            self.turn_counter += 1

        if too_heavy:
            msg = "That's too heavy for you to carry."
        elif full:
            msg = "Your pack cannot hold any more."
        else:
            noun = "items" if picked_up > 1 else "item"
            msg = f"Picked up {picked_up} {noun}."

        return StepResult(message=msg, reward=reward,
                          turn_used=picked_up > 0)

    def _handle_drop(self, letter: str) -> StepResult:
        if not letter:
            return StepResult(message="Drop what?")
        item = self.player.remove_from_inventory(letter)
        if item is None:
            return StepResult(message="You don't have that.")
        self.board.add_goodie(self.player.pos, item)
        self.turn_counter += 1
        # A dropped item thuds onto the floor — a soft but audible noise.
        self.board.emit_noise(self.player.pos, NOISE_DROP)
        return StepResult(message=f"Dropped {item.item_name}.",
                          turn_used=True)

    # ------------------------------------------------------------------
    # Doors
    # ------------------------------------------------------------------

    def _handle_door(self, direction: Direction,
                     opening: bool) -> StepResult:
        """Open or close a door.

        Opening a door creaks; closing thuds.  Both emit noise that
        draws nearby monsters — choose your moment carefully.
        """
        if direction == Direction.NONE:
            verb = "Open" if opening else "Close"
            return StepResult(message=f"{verb} in what direction?")
        dr, dc = DIRECTION_DELTA[direction]
        target = Coordinate(self.player.pos.r + dr, self.player.pos.c + dc)
        if opening:
            msg, noise_desc, noise_level = self.board.try_open_door(target)
        else:
            msg, noise_desc, noise_level = self.board.try_close_door_ext(target)
        # A turn is used if the action actually did something (flavor
        # messages always begin with a capital letter and aren't "There"
        # or "This" — but the reliable signal is whether noise was made).
        turn_used: bool = noise_level > 0
        if turn_used:
            self.turn_counter += 1
            self.board.emit_noise(
                target, noise_level,
                description=noise_desc, is_monster=False,
            )
        return StepResult(message=msg, turn_used=turn_used)

    def _handle_kick(self, direction: Direction) -> StepResult:
        """Kick a door to force it open.

        Kicking reverberates through stone corridors — everything in
        earshot hears it.  Stuck doors weaken with each blow.
        Kicking at nothing risks pulling a muscle.
        """
        if direction == Direction.NONE:
            return StepResult(message="Kick in what direction?")
        dr, dc = DIRECTION_DELTA[direction]
        target = Coordinate(self.player.pos.r + dr, self.player.pos.c + dc)
        msg, noise_desc, noise_level = self.board.try_kick_door(
            target, kick_bonus=self.player.kick_bonus(),
        )
        self.turn_counter += 1
        if noise_level > 0:
            self.board.emit_noise(
                target, noise_level,
                description=noise_desc, is_monster=False,
            )
        else:
            # Kicked at nothing — risk of self-injury.
            self.board.emit_noise(self.player.pos, NOISE_KICK)
            if self.rng.randint(1, 100) <= KICK_NOTHING_HURT_CHANCE:
                dmg: int = sum(
                    self.rng.randint(1, KICK_NOTHING_SIDES)
                    for _ in range(KICK_NOTHING_DICE)
                )
                self.player.take_damage(dmg)
                msg += " You strain your leg!" if msg else "You strain your leg!"
        return StepResult(message=msg, turn_used=True)

    # ------------------------------------------------------------------
    # Reading (spellbooks)
    # ------------------------------------------------------------------

    def _handle_read(self, letter: str) -> StepResult:
        """Read a spellbook from inventory.

        Teaches the school (or adds proficiency if already known),
        then the book crumbles to dust and is removed from inventory.
        """
        from game.items import Spellbook, ItemType
        if not letter:
            return StepResult(message="Read what?")
        from game.items import letter_to_index
        idx: int = letter_to_index(letter)
        if idx < 0 or idx >= len(self.player.inventory):
            return StepResult(message="You don't have that.")
        item = self.player.inventory[idx]
        if item is None:
            return StepResult(message="You don't have that.")
        if not isinstance(item, Spellbook):
            return StepResult(message="You can't read that.")
        # Learn the school or gain proficiency.
        _was_new, msg = self.player.magic.learn(item.school)
        # The spellbook crumbles to dust.
        self.player.inventory[idx] = None
        self.turn_counter += 1
        return StepResult(message=msg, turn_used=True)

    # ------------------------------------------------------------------
    # Magic
    # ------------------------------------------------------------------

    def _handle_cast(self, school: Optional[MagicSchool],
                     direction: Direction, *,
                     target_pos: Optional[Coordinate] = None,
                     spell_radius: int = -1) -> StepResult:
        """Cast a spell from *school*.

        *target_pos* is the player-selected target cell (from cursor
        targeting).  *spell_radius* is the chosen blast size (0=small,
        1=medium, 2=large) or -1 for "no choice" (tier-dependent).
        Checks concentration, rolls outcome, delegates to the
        school-specific resolver, applies self-damage and noise.
        """
        if school is None:
            return StepResult(message="Cast what?")

        state: SchoolState = self.player.magic.schools[school]
        if not state.known:
            name: str = SCHOOL_NAMES[school]
            return StepResult(message=f"You don't know {name} magic.")

        cost: int = state.concentration_cost
        cur_conc: int = self.player.current_traits[Trait.CONCENTRATION]
        if cur_conc < cost:
            msg: str = self.rng.choice(LOW_CONC_MESSAGES)
            return StepResult(message=msg)

        # Spend concentration.
        self.player.spend_concentration(cost)
        self.turn_counter += 1

        # Roll outcome based on proficiency.
        tier = state.tier
        outcome: CastOutcome = roll_outcome(tier, self.rng)

        # Dispatch to school-specific resolver.
        from game.spells_fire import resolve_fire
        if school == MagicSchool.FIRE:
            cast_result: CastResult = resolve_fire(
                self, direction, tier, outcome, self.rng,
                target_pos=target_pos, chosen_radius=spell_radius,
            )
        else:
            # Placeholder for unimplemented schools.
            cast_result = CastResult()
            verb: str = SCHOOL_CAST_VERBS.get(school, "invoke magic")
            cast_result.message = (f"You attempt to {verb}... "
                                   f"but nothing happens yet.")

        # Apply self-damage from backfire/wild.
        if cast_result.damage_taken > 0:
            self.player.take_damage(cast_result.damage_taken)

        # Emit noise from the cast.
        if cast_result.noise_level > 0:
            self.board.emit_noise(
                self.player.pos, cast_result.noise_level,
                description=cast_result.noise_desc, is_monster=False,
            )

        # Grant 1 proficiency XP for the cast.
        state.add_xp(1)

        result: StepResult = StepResult(
            message=cast_result.message,
            turn_used=True,
        )

        # Concentration spent info appended.
        conc_now: int = self.player.current_traits[Trait.CONCENTRATION]
        conc_max: int = self.player.maximum_traits[Trait.CONCENTRATION]
        result.message += f" [Conc: {conc_now}/{conc_max}]"

        return result

    # ------------------------------------------------------------------
    # Natural healing
    # ------------------------------------------------------------------

    def _heal_interval(self) -> int:
        """Turns between natural heals, based on Constitution.

        CON 18 → 10 turns, CON 12 → 30 turns, linear interpolation.
        """
        con: int = self.player.current_traits[Trait.CONSTITUTION]
        interval: int = HEAL_BASE_INTERVAL + (18 - con) * HEAL_CON_SCALE // 3
        return max(HEAL_BASE_INTERVAL, interval)

    def _any_monster_adjacent(self) -> bool:
        """True if any monster occupies a cell adjacent to the player."""
        pr: int = self.player.pos.r
        pc: int = self.player.pos.c
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                if dr == 0 and dc == 0:
                    continue
                nr: int = pr + dr
                nc: int = pc + dc
                if 0 <= nr < BOARD_ROWS and 0 <= nc < BOARD_COLUMNS:
                    if self.board.get_monster_at(Coordinate(nr, nc)) is not None:
                        return True
        return False

    def _try_natural_heal(self) -> str:
        """Heal 1 HP if enough turns have passed and no enemies are adjacent.

        Returns a message string if healing occurred, empty string otherwise.
        """
        if self.player.hp >= self.player.max_hp:
            self._last_heal_turn = self.turn_counter
            return ""
        if self._any_monster_adjacent():
            return ""
        elapsed: int = self.turn_counter - self._last_heal_turn
        if elapsed >= self._heal_interval():
            self._last_heal_turn = self.turn_counter
            self.player.heal(1)
            return ""
        return ""

    # ------------------------------------------------------------------
    # Concentration regeneration
    # ------------------------------------------------------------------

    def _conc_interval(self) -> int:
        """Turns between concentration restores, based on Intelligence.

        INT 18 → every 8 turns, INT 12 → every 24 turns.
        """
        intel: int = self.player.current_traits[Trait.INTELLIGENCE]
        interval: int = CONC_BASE_INTERVAL + (18 - intel) * CONC_INT_SCALE // 3
        return max(CONC_BASE_INTERVAL, interval)

    def _try_conc_regen(self) -> None:
        """Restore 1 concentration if enough turns have passed."""
        cur: int = self.player.current_traits[Trait.CONCENTRATION]
        mx: int = self.player.maximum_traits[Trait.CONCENTRATION]
        if cur >= mx:
            self._last_conc_turn = self.turn_counter
            return
        elapsed: int = self.turn_counter - self._last_conc_turn
        if elapsed >= self._conc_interval():
            self._last_conc_turn = self.turn_counter
            self.player.restore_concentration(1)

    # ------------------------------------------------------------------
    # Board management
    # ------------------------------------------------------------------

    def _new_board(self) -> None:
        """Generate and append a new dungeon level."""
        level: int = len(self.boards) + 1
        self.boards.append(Board(self.rng, level=level))

    # ------------------------------------------------------------------
    # ML observation interface
    # ------------------------------------------------------------------

    def get_observation(self) -> dict:
        """Return the full observable game state for an agent.

        This is the (state) part of the (state, action, reward) tuple.
        Includes visible monsters for the current level.
        """
        return {
            "board": self.board.get_state(),
            "player": self.player.get_state(),
            "turn": self.turn_counter,
            "dungeon_level": self.current_board_index + 1,
        }

    # ------------------------------------------------------------------
    # Save / load — pickle the entire engine state
    # ------------------------------------------------------------------

    SAVE_DIR: str = "~/.pnh"
    SAVE_FILE: str = "savegame.pkl"

    def save(self) -> str:
        """Serialize the full game state to disk.

        Returns the path written.  Clears transient noise events
        before saving so stale sounds don't replay on load.
        """
        for b in self.boards:
            b.clear_noise()
        save_dir: str = os.path.expanduser(self.SAVE_DIR)
        os.makedirs(save_dir, exist_ok=True)
        path: str = os.path.join(save_dir, self.SAVE_FILE)
        with open(path, "wb") as f:
            pickle.dump(self, f, protocol=pickle.HIGHEST_PROTOCOL)
        return path

    @classmethod
    def load(cls) -> Optional[GameEngine]:
        """Restore a saved game, or return None if no save exists.

        Re-initializes singletons (corner map, brain registry) that
        are not part of the pickled instance state.
        """
        path: str = os.path.join(
            os.path.expanduser(cls.SAVE_DIR), cls.SAVE_FILE
        )
        if not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            engine: GameEngine = pickle.load(f)
        # Re-establish module-level singletons.
        initialize_corner_map()
        BrainRegistry.init()
        # Re-register any brain instances that were serialized with
        # monster species so the registry can save them at shutdown.
        # Also backfill any attributes that were added to Monster /
        # Creature after the save was pickled — saves from older
        # revisions must keep working.
        for board in engine.boards:
            for monster in board.get_all_monsters():
                species = monster.species
                if species._brain is not None:
                    BrainRegistry._brains[species.name] = species._brain
                if not hasattr(monster, "senses"):
                    monster.senses = species.senses
        return engine

    @classmethod
    def delete_save(cls) -> None:
        """Remove the save file (called on player death)."""
        path: str = os.path.join(
            os.path.expanduser(cls.SAVE_DIR), cls.SAVE_FILE
        )
        if os.path.exists(path):
            os.remove(path)
