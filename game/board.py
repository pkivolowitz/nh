# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""Dungeon board: generation, navigation queries, line-of-sight, and items.

This module is the heart of the game engine.  It has *no* curses
dependency — all rendering is handled by the renderer module.
"""

from __future__ import annotations

__version__ = "0.1.0"

import math
import random
from typing import Optional

from game.constants import (
    BOARD_COLUMNS,
    BOARD_ROWS,
    MIN_ROOMS,
    MAX_ROOMS,
    CH_HLINE,
    CH_VLINE,
    CH_BULLET,
    DOWN_STAIRS,
    UP_STAIRS,
    DOOR_CLOSED_SYM,
    DEFAULT_TORCH_RADIUS,
    MONSTER_ROOM_CHANCE,
    TORCH_LIGHT_RADIUS,
    TORCH_ROOM_CHANCE,
    MAX_TORCHES_PER_ROOM,
    NOISE_WALL_ATTENUATION,
    NOISE_FAINT_THRESHOLD,
    NOISE_LOUD_THRESHOLD,
    STUCK_DOOR_MIN_KICKS,
    STUCK_DOOR_MAX_KICKS,
)
from game.cell import Cell, CellBaseType, DoorState
from game.coordinate import Coordinate
from game.effects import (
    TileEffect, EffectType,
    FIRE_DURATION, SCORCH_DURATION, FIRE_DAMAGE_PER_TURN,
)
from game.room import Room
from game.items import BaseItem, Spellbook, ItemType
from game.drawing_support import corner_map
from game.monster import Monster, MonsterSpecies, get_eligible_species


class NoiseEvent:
    """A sound emitted at *pos* with intensity *level*.

    ``description`` is used when the player hears the noise
    (e.g. "soft padding of paws").  ``is_monster`` distinguishes
    noise the player should be told about (monsters) from noise the
    player generated themselves (already known).
    """

    __slots__ = ("pos", "level", "description", "is_monster")

    def __init__(self, pos: "Coordinate", level: int,
                 description: str = "",
                 is_monster: bool = False) -> None:
        self.pos: Coordinate = pos
        self.level: int = level
        self.description: str = description
        self.is_monster: bool = is_monster


def _direction_word(dr: int, dc: int) -> str:
    """Convert a (row, col) delta sign pair to a compass word."""
    if dr < 0 and dc == 0:
        return "north"
    if dr > 0 and dc == 0:
        return "south"
    if dr == 0 and dc < 0:
        return "west"
    if dr == 0 and dc > 0:
        return "east"
    if dr < 0 and dc < 0:
        return "northwest"
    if dr < 0 and dc > 0:
        return "northeast"
    if dr > 0 and dc < 0:
        return "southwest"
    if dr > 0 and dc > 0:
        return "southeast"
    return "nearby"


def _sign(x: int) -> int:
    """Return -1, 0, or +1 for the sign of *x*."""
    return (x > 0) - (x < 0)


class Board:
    """One dungeon level.

    Construction generates the full level: rooms, walls, corridors,
    corners, doors, stairs, and floor items.
    """

    def __init__(self, rng: random.Random, level: int = 1) -> None:
        self.rng: random.Random = rng
        self.level: int = level
        self.cells: list[list[Cell]] = [
            [Cell() for _ in range(BOARD_COLUMNS)]
            for _ in range(BOARD_ROWS)
        ]
        self.rooms: list[Room] = []
        self.goodies: dict[Coordinate, list[BaseItem]] = {}
        self.monsters: dict[Coordinate, Monster] = {}
        self.torches: list[Coordinate] = []
        self.noise_sources: list[NoiseEvent] = []
        self.effects: dict[Coordinate, TileEffect] = {}
        self.upstairs: Coordinate = Coordinate()
        self.downstairs: Coordinate = Coordinate()
        self._create()

    # ------------------------------------------------------------------
    # Navigation queries (used by engine and AI agents)
    # ------------------------------------------------------------------

    def is_navigable(self, c: Coordinate) -> bool:
        """Can an entity step onto this coordinate right now?"""
        bt = self.cells[c.r][c.c].base_type
        if bt in (CellBaseType.ROOM, CellBaseType.CORRIDOR):
            return True
        if bt == CellBaseType.DOOR:
            return self.is_door_passable(c)
        return False

    def is_door(self, c: Coordinate) -> bool:
        """Is this cell a door?"""
        return self.cells[c.r][c.c].base_type == CellBaseType.DOOR

    def is_door_passable(self, c: Coordinate) -> bool:
        """Is the door at *c* currently allowing passage?"""
        ds = self.cells[c.r][c.c].door_state
        return ds in (DoorState.DOOR_MISSING, DoorState.DOOR_OPEN)

    def is_a_stairway(self, c: Coordinate) -> bool:
        """Does this cell contain either staircase?"""
        if not (0 <= c.r < BOARD_ROWS and 0 <= c.c < BOARD_COLUMNS):
            return False
        oc = self.cells[c.r][c.c].original_c
        return oc == UP_STAIRS or oc == DOWN_STAIRS

    def is_downstairs(self, c: Coordinate) -> bool:
        """Is this the level's downward staircase?"""
        return self.is_a_stairway(c) and self.cells[c.r][c.c].original_c == DOWN_STAIRS

    def is_upstairs(self, c: Coordinate) -> bool:
        """Is this the level's upward staircase?"""
        return self.is_a_stairway(c) and self.cells[c.r][c.c].original_c == UP_STAIRS

    def is_corridor(self, c: Coordinate) -> bool:
        """Is this cell a corridor?"""
        return self.cells[c.r][c.c].base_type == CellBaseType.CORRIDOR

    def is_empty(self, c: Coordinate) -> bool:
        """Is this cell still empty / ungenerated?"""
        return self.cells[c.r][c.c].base_type == CellBaseType.EMPTY

    # ------------------------------------------------------------------
    # Item management
    # ------------------------------------------------------------------

    def add_goodie(self, c: Coordinate, item: BaseItem) -> None:
        """Place an item on the floor at *c*, stacking if possible."""
        pile: list[BaseItem] = self.goodies.setdefault(c, [])
        for existing in pile:
            if existing.can_stack_with(item):
                existing.number_of_like_items += item.number_of_like_items
                return
        pile.append(item)

    def remove_goodies(self, c: Coordinate) -> list[BaseItem]:
        """Remove and return all items at *c*."""
        return self.goodies.pop(c, [])

    def get_goodie_count(self, c: Coordinate) -> int:
        """How many items are stacked at *c*?"""
        return len(self.goodies.get(c, []))

    def get_symbol(self, c: Coordinate) -> int:
        """Visible symbol for the top item at *c*, or -1 if none."""
        items = self.goodies.get(c)
        if items:
            return items[-1].symbol
        return -1

    # ------------------------------------------------------------------
    # Monster management
    # ------------------------------------------------------------------

    def add_monster(self, monster: Monster) -> None:
        """Place a monster on the board at its current position."""
        self.monsters[monster.pos] = monster

    def remove_monster(self, pos: Coordinate) -> Optional[Monster]:
        """Remove and return the monster at *pos*, or None."""
        return self.monsters.pop(pos, None)

    def get_monster_at(self, pos: Coordinate) -> Optional[Monster]:
        """Return the monster at *pos*, or None."""
        return self.monsters.get(pos)

    def get_all_monsters(self) -> list[Monster]:
        """Return a snapshot list of all living monsters on this level."""
        return list(self.monsters.values())

    def get_monsters_near(self, pos: Coordinate,
                          radius: float) -> list[Monster]:
        """Return monsters within *radius* Euclidean distance of *pos*."""
        return [
            m for m in self.monsters.values()
            if m.pos.distance(pos) <= radius
        ]

    def move_monster(self, monster: Monster,
                     new_pos: Coordinate) -> None:
        """Relocate a monster from its current cell to *new_pos*."""
        self.monsters.pop(monster.pos, None)
        monster.pos = new_pos
        self.monsters[new_pos] = monster

    # ------------------------------------------------------------------
    # Noise system — actions emit sound that monsters and the player hear
    # ------------------------------------------------------------------

    def emit_noise(self, pos: Coordinate, level: int,
                   description: str = "",
                   is_monster: bool = False) -> None:
        """Register a noise event at *pos*.

        The noise persists until cleared (typically at the start of
        the next game step).  ``description`` and ``is_monster`` are
        used when generating hear messages for the player.
        """
        self.noise_sources.append(
            NoiseEvent(pos, level, description, is_monster)
        )

    def clear_noise(self) -> None:
        """Discard all pending noise events."""
        self.noise_sources.clear()

    def noise_at(self, pos: Coordinate) -> tuple[float, Optional[Coordinate]]:
        """Return (loudest heard level, source position) at *pos*.

        Returns (0.0, None) if nothing is audible.  Used by monster
        brains to perceive nearby noises.
        """
        best_level: float = 0.0
        best_source: Optional[Coordinate] = None
        for event in self.noise_sources:
            heard: float = self._noise_propagation(
                event.pos, pos, event.level
            )
            if heard > best_level:
                best_level = heard
                best_source = event.pos
        return best_level, best_source

    def _noise_propagation(self, source: Coordinate, target: Coordinate,
                           level: int) -> float:
        """How much of *level* noise at *source* reaches *target*.

        Attenuation = Euclidean distance + (walls crossed * wall penalty).
        Clamped at zero; inaudible returns 0.
        """
        if source.r == target.r and source.c == target.c:
            return float(level)
        dist: float = source.distance(target)
        walls: int = self._walls_along_path(source, target)
        heard: float = level - dist - walls * NOISE_WALL_ATTENUATION
        return max(0.0, heard)

    def _walls_along_path(self, source: Coordinate,
                          target: Coordinate) -> int:
        """Count wall and closed-door cells along the straight line.

        The source and target cells themselves are not counted.
        """
        dist: float = source.distance(target)
        if dist <= 1.0:
            return 0
        delta: float = 1.0 / (dist + 1.0)
        t: float = delta
        walls: int = 0
        seen: set[tuple[int, int]] = set()
        src_key: tuple[int, int] = (source.r, source.c)
        tgt_key: tuple[int, int] = (target.r, target.c)
        while t < 1.0:
            s = source.lerp(target, t)
            key: tuple[int, int] = (s.r, s.c)
            if key in seen or key == src_key or key == tgt_key:
                t += delta
                continue
            seen.add(key)
            cell = self.cells[s.r][s.c]
            if cell.base_type == CellBaseType.WALL:
                walls += 1
            elif (cell.base_type == CellBaseType.DOOR
                  and cell.door_state in (DoorState.DOOR_CLOSED,
                                          DoorState.DOOR_LOCKED,
                                          DoorState.DOOR_STUCK)):
                walls += 1
            t += delta
        return walls

    def get_player_hear_messages(self, player_pos: Coordinate,
                                 player_tr: float) -> list[str]:
        """Build hear messages for monster noises audible at *player_pos*.

        Only includes monster-sourced noise the player can't already
        see (no point reporting what you can visually track).
        Deduplicates by (description, direction) so multiple jackals
        moving south produce one message, not many.
        """
        heard_sounds: dict[tuple[str, str], float] = {}

        for event in self.noise_sources:
            if not event.is_monster:
                continue
            if not event.description:
                continue

            # Skip if the player can currently see this position.
            visible: bool = (
                event.pos.distance(player_pos) < player_tr
                and self.line_of_sight(player_pos, event.pos)
            )
            if not visible:
                ecell = self.cells[event.pos.r][event.pos.c]
                visible = (ecell.lit
                           and self.line_of_sight(player_pos, event.pos))
            if visible:
                continue

            heard: float = self._noise_propagation(
                event.pos, player_pos, event.level
            )
            if heard < NOISE_FAINT_THRESHOLD:
                continue

            dr: int = _sign(event.pos.r - player_pos.r)
            dc: int = _sign(event.pos.c - player_pos.c)
            direction: str = _direction_word(dr, dc)
            key: tuple[str, str] = (event.description, direction)
            if heard > heard_sounds.get(key, 0.0):
                heard_sounds[key] = heard

        messages: list[str] = []
        for (description, direction), level in heard_sounds.items():
            if level >= NOISE_LOUD_THRESHOLD:
                messages.append(
                    f"You hear a loud {description} to your {direction}!"
                )
            else:
                messages.append(
                    f"You hear a {description} to your {direction}."
                )
        return messages

    # ------------------------------------------------------------------
    # Ephemeral tile effects
    # ------------------------------------------------------------------

    def add_fire(self, pos: Coordinate) -> list[str]:
        """Place a fire effect at *pos* and incinerate flammable goodies.

        Fire burns doors in stages:
            intact → charred (retains open/closed state)
            charred → missing (destroyed completely)
        A charred closed door still blocks — burn it again or kick it
        to destroy.  A charred open door can't be closed.
        Fire replaces any existing effect at this cell.

        Flammable items (spellbooks, scrolls, food) on the cell are
        consumed.  Potions survive (glass).  Returns descriptions of
        any items destroyed so the caller can report them.
        """
        cell = self.cells[pos.r][pos.c]
        if cell.base_type == CellBaseType.DOOR:
            if cell.door_charred:
                # Already charred — next fire destroys it.
                cell.door_state = DoorState.DOOR_MISSING
                cell.door_charred = False
                self._update_door_display(pos.r, pos.c)
            elif cell.door_state != DoorState.DOOR_MISSING:
                # First fire chars the door but keeps its state.
                cell.door_charred = True
                self._update_door_display(pos.r, pos.c)

        burned: list[str] = []
        pile = self.goodies.get(pos)
        if pile:
            survivors: list[BaseItem] = []
            for item in pile:
                if item.type == ItemType.POTION:
                    survivors.append(item)
                else:
                    burned.append(item.describe())
            if survivors:
                self.goodies[pos] = survivors
            else:
                del self.goodies[pos]

        self.effects[pos] = TileEffect(
            EffectType.FIRE, pos, FIRE_DURATION, FIRE_DAMAGE_PER_TURN
        )
        return burned

    def tick_effects(self) -> list[str]:
        """Advance all effects by one turn.

        Returns messages about environmental interactions (e.g.
        monsters burning).  Expired fire effects leave scorch marks.
        """
        messages: list[str] = []
        expired: list[Coordinate] = []
        replacements: list[TileEffect] = []

        for pos, effect in self.effects.items():
            # Damage monsters standing in fire.
            if effect.effect_type == EffectType.FIRE and effect.damage_per_turn > 0:
                monster = self.get_monster_at(pos)
                if monster is not None and monster.is_alive:
                    monster.take_damage(effect.damage_per_turn)
                    if not monster.is_alive:
                        from game.brain import REWARD_DEATH
                        brain = monster.species.get_brain()
                        if monster.last_action is not None:
                            brain.record_outcome(
                                monster, monster.last_action, REWARD_DEATH,
                                None  # No engine ref needed for death recording.
                            )
                        self.remove_monster(pos)
                        messages.append(
                            f"The {monster.name} burns to death in the flames!"
                        )
                    else:
                        messages.append(
                            f"The {monster.name} burns in the flames!"
                        )

            effect.tick()
            if effect.is_expired:
                expired.append(pos)
                # Fire leaves scorch marks.
                if effect.effect_type == EffectType.FIRE:
                    replacements.append(TileEffect(
                        EffectType.SCORCH, pos, SCORCH_DURATION
                    ))

        # Remove expired, add replacements.
        for pos in expired:
            del self.effects[pos]
        for eff in replacements:
            self.effects[eff.pos] = eff

        return messages

    def get_effect_at(self, pos: Coordinate) -> TileEffect | None:
        """Return the active effect at *pos*, or None."""
        return self.effects.get(pos)

    # ------------------------------------------------------------------
    # Monster spawning (called by engine after player placement)
    # ------------------------------------------------------------------

    def place_monsters(self, player_pos: Coordinate,
                       dungeon_level: int) -> None:
        """Spawn monsters on this level.

        Monsters never spawn in the room containing *player_pos*.
        Pack species spawn in groups of 2-4.
        """
        eligible: list[MonsterSpecies] = get_eligible_species(dungeon_level)
        if not eligible:
            return

        player_room: int = self.cells[player_pos.r][player_pos.c].final_room_number

        for rm in self.rooms:
            centroid: Coordinate = rm.get_centroid()
            room_id: int = self.cells[centroid.r][centroid.c].final_room_number
            if room_id == player_room:
                continue

            # Roll whether this room gets monsters.
            if self.rng.randint(1, 100) > MONSTER_ROOM_CHANCE:
                continue

            species: MonsterSpecies = self._pick_species(eligible)

            # Pack species spawn in groups; solo species spawn alone.
            count: int = 1
            if "pack" in species.flags:
                count = self.rng.randint(
                    species.spawn_group_min, species.spawn_group_max
                )

            positions: list[Coordinate] = self._find_monster_positions(rm, count)
            for pos in positions:
                monster: Monster = Monster(species, pos, self.rng)
                self.add_monster(monster)

    def _pick_species(self,
                      eligible: list[MonsterSpecies]) -> MonsterSpecies:
        """Choose a species weighted by spawn frequency."""
        total_freq: int = sum(s.frequency for s in eligible)
        roll: int = self.rng.randint(1, total_freq)
        cumulative: int = 0
        for s in eligible:
            cumulative += s.frequency
            if roll <= cumulative:
                return s
        return eligible[-1]

    def _find_monster_positions(self, room: Room,
                                count: int) -> list[Coordinate]:
        """Find valid floor positions in *room* for monster placement."""
        candidates: list[Coordinate] = []
        for r in range(room.tl.r, room.br.r):
            for c in range(room.tl.c, room.br.c):
                coord: Coordinate = Coordinate(r, c)
                if (self.is_navigable(coord)
                        and not self.is_a_stairway(coord)
                        and coord not in self.monsters
                        and coord not in self.goodies):
                    candidates.append(coord)
        self.rng.shuffle(candidates)
        return candidates[:count]

    # ------------------------------------------------------------------
    # Door interaction
    # ------------------------------------------------------------------

    # Atmospheric descriptions for door sounds — picked at random to
    # keep repeated opens from feeling mechanical.  Each tuple is
    # (player message fragment, noise description heard from afar).
    _DOOR_OPEN_FLAVOR: list[tuple[str, str]] = [
        ("A rusty hinge protests as you pull it open.",
         "the protest of a rusty hinge"),
        ("The door groans open on old hinges.",
         "the groan of old wood"),
        ("Hinges shriek as the door swings wide.",
         "a shriek of metal on metal"),
        ("The door creaks open reluctantly.",
         "a reluctant creak of hinges"),
        ("You ease the door open; the hinges whine softly.",
         "the soft whine of hinges"),
    ]

    _DOOR_CLOSE_FLAVOR: list[tuple[str, str]] = [
        ("The door thuds shut.",
         "the thud of a closing door"),
        ("You pull the door closed; the latch clicks.",
         "the click of a door latch"),
        ("The door settles into its frame with a dull boom.",
         "a dull boom from somewhere"),
    ]

    # Escalating messages as a stuck door weakens under repeated kicks.
    _STUCK_KICK_PROGRESS: list[str] = [
        "The door shudders but holds.",
        "The hinges groan under the impact — something gives a little.",
        "Wood splinters at the frame. One more ought to do it.",
        "The door buckles, barely clinging to its hinges.",
    ]

    _STUCK_BREAK_FLAVOR: list[tuple[str, str]] = [
        ("The door bursts inward with a splintering crash!",
         "the crack of splintering wood"),
        ("The frame gives way and the door flies open!",
         "a thunderous crack of breaking timber"),
        ("With a final kick the door tears free of its hinges!",
         "the shriek of hinges tearing loose"),
    ]

    def try_open_door(self, c: Coordinate) -> tuple[str, str, int]:
        """Attempt to open the door at *c*.

        Returns (player_message, noise_description, noise_level).
        noise_level == 0 means no noise should be emitted.
        """
        if not (0 <= c.r < BOARD_ROWS and 0 <= c.c < BOARD_COLUMNS):
            return "There is nothing there to open.", "", 0
        cell = self.cells[c.r][c.c]
        if cell.base_type != CellBaseType.DOOR:
            return "There is nothing there to open.", "", 0
        if cell.door_state in (DoorState.DOOR_OPEN, DoorState.DOOR_MISSING):
            return "This door is already open.", "", 0
        if cell.door_charred:
            return "The charred door is jammed. Try kicking it.", "", 0
        if cell.door_state == DoorState.DOOR_LOCKED:
            return "This door is locked.", "", 0
        if cell.door_state == DoorState.DOOR_STUCK:
            return "The door is stuck!", "", 0
        if cell.door_state == DoorState.DOOR_CLOSED:
            cell.door_state = DoorState.DOOR_OPEN
            self._update_door_display(c.r, c.c)
            flavor, noise_desc = self.rng.choice(self._DOOR_OPEN_FLAVOR)
            from game.constants import NOISE_DOOR_OPEN
            return flavor, noise_desc, NOISE_DOOR_OPEN
        return "", "", 0

    def try_close_door_ext(self, c: Coordinate) -> tuple[str, str, int]:
        """Attempt to close the door at *c*.

        Returns (player_message, noise_description, noise_level).
        """
        if not (0 <= c.r < BOARD_ROWS and 0 <= c.c < BOARD_COLUMNS):
            return "There is nothing there to close.", "", 0
        cell = self.cells[c.r][c.c]
        if cell.base_type != CellBaseType.DOOR:
            return "There is nothing there to close.", "", 0
        if cell.door_state in (DoorState.DOOR_CLOSED, DoorState.DOOR_LOCKED,
                               DoorState.DOOR_STUCK):
            return "This door is already closed.", "", 0
        if cell.door_state == DoorState.DOOR_MISSING:
            return "There is no door there to close.", "", 0
        if cell.door_charred:
            return "The charred door no longer operates.", "", 0
        if cell.door_state == DoorState.DOOR_OPEN:
            cell.door_state = DoorState.DOOR_CLOSED
            self._update_door_display(c.r, c.c)
            flavor, noise_desc = self.rng.choice(self._DOOR_CLOSE_FLAVOR)
            from game.constants import NOISE_DOOR_CLOSE
            return flavor, noise_desc, NOISE_DOOR_CLOSE
        return "", "", 0

    def try_kick_door(self, c: Coordinate,
                      kick_bonus: int = 0) -> tuple[str, str, int]:
        """Kick the door at *c*.  Can force stuck and locked doors.

        *kick_bonus* is an additive percentage from STRENGTH applied to
        locked and closed door success rolls.  Stuck doors track
        remaining kicks and yield with escalating drama.
        Returns (player_message, noise_description, noise_level).
        """
        from game.constants import NOISE_KICK, NOISE_DOOR_BREAK
        if not (0 <= c.r < BOARD_ROWS and 0 <= c.c < BOARD_COLUMNS):
            return "You kick at nothing.", "", 0
        cell = self.cells[c.r][c.c]
        if cell.base_type != CellBaseType.DOOR:
            return "You kick at nothing.", "", 0
        if cell.door_state in (DoorState.DOOR_OPEN, DoorState.DOOR_MISSING):
            if not cell.door_charred:
                return "That door is already open.", "", 0

        # Charred doors crumble with one kick regardless of state.
        if cell.door_charred:
            cell.door_state = DoorState.DOOR_MISSING
            cell.door_charred = False
            self._update_door_display(c.r, c.c)
            return ("The charred door crumbles to pieces!",
                    "splintering wood", NOISE_DOOR_BREAK)

        # Stuck doors use the deterministic kick counter.
        if cell.door_state == DoorState.DOOR_STUCK:
            cell.door_kicks_remaining -= 1
            if cell.door_kicks_remaining <= 0:
                cell.door_state = DoorState.DOOR_OPEN
                self._update_door_display(c.r, c.c)
                flavor, noise_desc = self.rng.choice(self._STUCK_BREAK_FLAVOR)
                return flavor, noise_desc, NOISE_DOOR_BREAK
            # Pick a progress message based on how close the door is to breaking.
            idx = min(len(self._STUCK_KICK_PROGRESS) - 1,
                      STUCK_DOOR_MAX_KICKS - cell.door_kicks_remaining - 1)
            return self._STUCK_KICK_PROGRESS[idx], "a heavy impact on wood", NOISE_KICK

        # Locked doors: probabilistic (no counter).  STR bonus helps.
        if cell.door_state == DoorState.DOOR_LOCKED:
            if self.rng.randint(1, 100) <= 25 + kick_bonus:
                cell.door_state = DoorState.DOOR_OPEN
                self._update_door_display(c.r, c.c)
                return ("The lock snaps and the door swings open!",
                        "the snap of a breaking lock", NOISE_DOOR_BREAK)
            return ("The lock holds against the blow.",
                    "a heavy impact on wood", NOISE_KICK)

        # Closed doors: easy to kick open.  STR bonus helps.
        if cell.door_state == DoorState.DOOR_CLOSED:
            if self.rng.randint(1, 100) <= 80 + kick_bonus:
                cell.door_state = DoorState.DOOR_OPEN
                self._update_door_display(c.r, c.c)
                flavor, noise_desc = self.rng.choice(self._STUCK_BREAK_FLAVOR)
                return flavor, noise_desc, NOISE_DOOR_BREAK
            return ("The door rattles but stays shut.",
                    "a heavy impact on wood", NOISE_KICK)

        return "The door resists.", "", 0

    # ------------------------------------------------------------------
    # Visibility (curses-free)
    # ------------------------------------------------------------------

    def update_visibility(self, pos: Coordinate,
                          tr: float = DEFAULT_TORCH_RADIUS) -> None:
        """Mark cells visible from *pos* as known.

        A cell is visible if the player has line of sight to it AND
        either:
          - it lies within the player's personal torch radius, OR
          - it is illuminated by a dungeon torch (cell.lit is True).

        This means the player sees lit areas across the room even
        when they're well beyond personal torch range.
        """
        for r in range(BOARD_ROWS):
            for c in range(BOARD_COLUMNS):
                cell = self.cells[r][c]
                if cell.base_type == CellBaseType.EMPTY:
                    continue
                if cell.is_known:
                    continue
                coord = Coordinate(r, c)
                within_personal: bool = coord.distance(pos) < tr
                if not (within_personal or cell.lit):
                    continue
                if not self.line_of_sight(pos, coord):
                    continue
                cell.is_known = True

    # ------------------------------------------------------------------
    # Line of sight
    # ------------------------------------------------------------------

    def line_of_sight(self, origin: Coordinate, target: Coordinate) -> bool:
        """Trace a coarse ray from *origin* to *target*.

        Returns False if the ray hits a wall, empty cell, or closed door.
        """
        dist = origin.distance(target)
        if dist <= 1:
            return True
        delta = 1.0 / (dist + 1.0)
        t = 0.0
        while t < 1.0:
            s = origin.lerp(target, t)
            cell = self.cells[s.r][s.c]
            door_blocks = (
                cell.base_type == CellBaseType.DOOR
                and cell.door_state not in (DoorState.DOOR_OPEN,
                                            DoorState.DOOR_MISSING)
            )
            if cell.base_type in (CellBaseType.EMPTY, CellBaseType.WALL) or door_blocks:
                return False
            t += delta
        return True

    # ------------------------------------------------------------------
    # State for ML agents
    # ------------------------------------------------------------------

    def get_state(self) -> dict:
        """Return a machine-readable snapshot of the board.

        Keys:
            cells:      list[list[dict]] — base_type, is_known, door_state per cell
            goodies:    dict mapping (r, c) → count of items
            upstairs:   (r, c)
            downstairs: (r, c)
            rooms:      list of (tl_r, tl_c, br_r, br_c)
        """
        cell_state = []
        for r in range(BOARD_ROWS):
            row = []
            for c in range(BOARD_COLUMNS):
                cell = self.cells[r][c]
                row.append({
                    "base_type": int(cell.base_type),
                    "is_known": cell.is_known,
                    "door_state": int(cell.door_state),
                    "stair": (cell.original_c == UP_STAIRS or
                              cell.original_c == DOWN_STAIRS),
                })
            cell_state.append(row)

        return {
            "cells": cell_state,
            "goodies": {(k.r, k.c): len(v) for k, v in self.goodies.items()},
            "upstairs": self.upstairs.to_tuple(),
            "downstairs": self.downstairs.to_tuple(),
            "rooms": [(rm.tl.r, rm.tl.c, rm.br.r, rm.br.c)
                      for rm in self.rooms],
            "monsters": [m.get_state() for m in self.monsters.values()],
        }

    # ==================================================================
    # Private — level generation
    # ==================================================================

    def _create(self) -> None:
        """Generate the full contents of a level from scratch."""
        room_count = self.rng.randint(MIN_ROOMS, MAX_ROOMS)
        self.rooms = [Room() for _ in range(room_count)]
        for i, rm in enumerate(self.rooms):
            rm.initialize(i, self.rng)
            self._fill(i)
            self._enclose(i)
        self._place_corners()
        self._place_corridors()
        self._place_doors()
        self._flatten_rooms()
        self._place_torches()
        self._place_stairs()
        self._place_goodies(guarantee_fire=(self.level == 1))

    # -- room fill / enclose -------------------------------------------

    def _fill(self, rn: int) -> None:
        """Fill every interior tile of room *rn* with its room digit."""
        rm = self.rooms[rn]
        for r in range(rm.tl.r, rm.br.r):
            for c in range(rm.tl.c, rm.br.c):
                cell = self.cells[r][c]
                cell.original_c = ord("0") + rn
                cell.display_c = ord("0") + rn
                cell.base_type = CellBaseType.ROOM

    def _enclose(self, rn: int) -> None:
        """Surround a room's interior with wall cells."""
        rm = self.rooms[rn]
        # Vertical walls (left and right).
        for r in range(rm.tl.r, rm.br.r):
            if self.cells[r][rm.tl.c - 1].original_c == 0:
                self._set_cell(self.cells[r][rm.tl.c - 1],
                               CellBaseType.WALL, CH_VLINE)
            if self.cells[r][rm.br.c].original_c == 0:
                self._set_cell(self.cells[r][rm.br.c],
                               CellBaseType.WALL, CH_VLINE)
        # Horizontal walls (top and bottom).
        for c in range(rm.tl.c - 1, rm.br.c + 1):
            if self.cells[rm.tl.r - 1][c].original_c == 0:
                self._set_cell(self.cells[rm.tl.r - 1][c],
                               CellBaseType.WALL, CH_HLINE)
            if self.cells[rm.br.r][c].original_c == 0:
                self._set_cell(self.cells[rm.br.r][c],
                               CellBaseType.WALL, CH_HLINE)

    @staticmethod
    def _set_cell(cell: Cell, bt: CellBaseType, ch: int) -> None:
        """Initialize a cell's type and display character together."""
        cell.base_type = bt
        cell.original_c = ch

    # -- corridors -----------------------------------------------------

    def _find_rows_to_avoid(self) -> list[int]:
        """Rows containing horizontal wall segments (avoid corridor overlap)."""
        avoid: list[int] = []
        for r in range(BOARD_ROWS):
            for c in range(BOARD_COLUMNS):
                if self.cells[r][c].original_c == CH_HLINE:
                    avoid.append(r)
                    break
        return avoid

    def _find_cols_to_avoid(self) -> list[int]:
        """Columns containing vertical wall segments."""
        avoid: list[int] = []
        for c in range(BOARD_COLUMNS):
            for r in range(BOARD_ROWS):
                if self.cells[r][c].original_c == CH_VLINE:
                    avoid.append(c)
                    break
        return avoid

    def _find_good_coords(self, bad_rows: list[int], bad_cols: list[int],
                          rm: Room) -> Optional[Coordinate]:
        """Pick a corridor endpoint inside *rm* avoiding ugly wall-hugging."""
        cols_in_room = list(range(rm.tl.c, rm.br.c))
        rows_in_room = list(range(rm.tl.r, rm.br.r))
        self.rng.shuffle(cols_in_room)
        self.rng.shuffle(rows_in_room)

        good_c = -1
        for c in cols_in_room:
            if c not in bad_cols:
                good_c = c
                break

        good_r = -1
        for r in rows_in_room:
            if r not in bad_rows:
                good_r = r
                break

        if good_c < 0 or good_r < 0:
            return None
        return Coordinate(good_r, good_c)

    def _place_corridors(self) -> None:
        """Connect rooms in sequence with L-shaped corridors."""
        bad_cols = self._find_cols_to_avoid()
        bad_rows = self._find_rows_to_avoid()

        needs_plan_b: list[int] = []
        key_points: list[Coordinate] = []

        for rm in self.rooms:
            coord = self._find_good_coords(bad_rows, bad_cols, rm)
            if coord is None:
                needs_plan_b.append(rm.room_number)
                continue
            key_points.append(coord)

        for i in range(len(key_points) - 1):
            self._lay_corridor(key_points[i], key_points[i + 1])

        for rn in needs_plan_b:
            self._plan_b_corridor(rn)

    def _make_corridor_cell(self, cell: Cell) -> None:
        """Convert a cell into corridor floor, noting wall-to-corridor breaks."""
        # Skip cells that are already room interior (digit markers).
        if 0 < cell.original_c < 256 and chr(cell.original_c).isdigit():
            return
        was_wall = cell.base_type == CellBaseType.WALL
        cell.display_c = cell.original_c = ord("#")
        cell.base_type = CellBaseType.CORRIDOR
        cell.final_room_number = -1
        if was_wall:
            cell.door_state = DoorState.DOOR_CLOSED  # Placeholder for _place_doors.

    def _make_corridor_at(self, r: int, c: int) -> None:
        """Convert the cell at (r, c) into corridor floor."""
        self._make_corridor_cell(self.cells[r][c])

    def _lay_corridor(self, src: Coordinate, dst: Coordinate) -> None:
        """Carve an L-shaped corridor between *src* and *dst*."""
        seeds: list[Coordinate] = []

        # Horizontal leg — iterate through dst.c so the corridor
        # punches through the destination room's wall.
        if src.c != dst.c:
            dc = 1 if src.c < dst.c else -1
            r = src.r
            c = src.c
            end_c = dst.c + dc
            while c != end_c:
                if c < 0 or c >= BOARD_COLUMNS:
                    break
                self._make_corridor_at(r, c)
                if self.rng.randint(1, 100) < 3:
                    seeds.append(Coordinate(r, c))
                c += dc

        # Random short branches off the horizontal leg.
        for s in seeds:
            key = self._build_corner_key(s.r, s.c)
            if key == "         ":
                delta_r = 1 if self.rng.randint(0, 1) else -1
                nspaces = self.rng.randint(1, 3)
                while nspaces > 0:
                    s = Coordinate(s.r + delta_r, s.c)
                    if s.r < 0 or s.r >= BOARD_ROWS:
                        break
                    if not self.is_empty(s):
                        break
                    self._make_corridor_at(s.r, s.c)
                    nspaces -= 1

        # Vertical leg — same: iterate through dst.r.
        if src.r != dst.r:
            dr = 1 if src.r < dst.r else -1
            c = dst.c
            r = src.r
            end_r = dst.r + dr
            while r != end_r:
                if r < 0 or r >= BOARD_ROWS:
                    break
                self._make_corridor_at(r, c)
                r += dr

    def _plan_b_corridor(self, room_index: int) -> None:
        """Fallback: connect an orphaned room to its nearest neighbour."""
        src = self.rooms[room_index].get_centroid()
        smallest_dist = float("inf")
        closest = 0
        for i, rm in enumerate(self.rooms):
            if i == room_index:
                continue
            dst = rm.get_centroid()
            d = src.distance(dst)
            if d < smallest_dist:
                smallest_dist = d
                closest = i
        dst = self.rooms[closest].get_centroid()
        self._lay_corridor(src, dst)

    # -- corners -------------------------------------------------------

    def _build_corner_key(self, r: int, c: int) -> str:
        """Build the 9-char neighbourhood key for the corner map."""
        key_chars: list[str] = []
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                nr, nc = r + dr, c + dc
                if nr < 0 or nr >= BOARD_ROWS or nc < 0 or nc >= BOARD_COLUMNS:
                    key_chars.append(" ")
                elif self.cells[nr][nc].original_c == 0:
                    key_chars.append(" ")
                elif (self.cells[nr][nc].original_c < 256
                      and chr(self.cells[nr][nc].original_c).isdigit()):
                    key_chars.append("F")
                elif self.cells[nr][nc].original_c == CH_HLINE:
                    key_chars.append("H")
                elif self.cells[nr][nc].original_c == CH_VLINE:
                    key_chars.append("V")
                else:
                    key_chars.append(" ")
        return "".join(key_chars)

    def _place_corners(self) -> None:
        """Replace wall junctions with the correct line-drawing constant."""
        for r in range(BOARD_ROWS):
            for c in range(BOARD_COLUMNS):
                key = self._build_corner_key(r, c)
                if key in corner_map:
                    self.cells[r][c].display_c = corner_map[key]
                else:
                    self.cells[r][c].display_c = self.cells[r][c].original_c

    # -- doors ---------------------------------------------------------

    def _place_doors(self) -> None:
        """Convert wall-to-corridor break points into doors."""
        for r in range(BOARD_ROWS):
            for c in range(BOARD_COLUMNS):
                cell = self.cells[r][c]
                if cell.door_state == DoorState.DOOR_NONE:
                    continue
                if cell.base_type != CellBaseType.CORRIDOR:
                    continue

                room_above = (r > 0 and
                              self.cells[r - 1][c].base_type == CellBaseType.ROOM)
                room_below = (r < BOARD_ROWS - 1 and
                              self.cells[r + 1][c].base_type == CellBaseType.ROOM)
                room_left = (c > 0 and
                             self.cells[r][c - 1].base_type == CellBaseType.ROOM)
                room_right = (c < BOARD_COLUMNS - 1 and
                              self.cells[r][c + 1].base_type == CellBaseType.ROOM)

                vert_door = (room_above and not room_below) or (room_below and not room_above)
                horiz_door = (room_left and not room_right) or (room_right and not room_left)

                if not vert_door and not horiz_door:
                    cell.door_state = DoorState.DOOR_NONE
                    continue

                cell.base_type = CellBaseType.DOOR
                cell.door_horizontal = vert_door

                roll = self.rng.randint(1, 100)
                if roll <= 20:
                    cell.door_state = DoorState.DOOR_MISSING
                elif roll <= 50:
                    cell.door_state = DoorState.DOOR_OPEN
                elif roll <= 75:
                    cell.door_state = DoorState.DOOR_CLOSED
                elif roll <= 90:
                    cell.door_state = DoorState.DOOR_STUCK
                    # Stuck doors yield after a random number of kicks.
                    cell.door_kicks_remaining = self.rng.randint(
                        STUCK_DOOR_MIN_KICKS, STUCK_DOOR_MAX_KICKS
                    )
                else:
                    cell.door_state = DoorState.DOOR_LOCKED

                self._update_door_display(r, c)

    def _update_door_display(self, r: int, c: int) -> None:
        """Refresh a door cell's display character after state change."""
        cell = self.cells[r][c]
        if cell.door_state == DoorState.DOOR_MISSING:
            cell.display_c = ord("#")
        elif cell.door_charred:
            # Blackened frame — visually damaged regardless of open/closed.
            cell.display_c = ord("'")
        elif cell.door_state == DoorState.DOOR_OPEN:
            cell.display_c = ord("|") if cell.door_horizontal else ord("-")
        elif cell.door_state in (DoorState.DOOR_CLOSED,
                                 DoorState.DOOR_LOCKED,
                                 DoorState.DOOR_STUCK):
            cell.display_c = DOOR_CLOSED_SYM
        cell.original_c = cell.display_c

    # -- flatten rooms -------------------------------------------------

    def _flatten_rooms(self) -> None:
        """Flood-fill overlapping rooms so they share one final room id."""
        for room_index, rm in enumerate(self.rooms):
            c = rm.get_centroid()
            if self.cells[c.r][c.c].has_been_flattened:
                continue
            flattened_value = rm.room_number
            work_list: list[Coordinate] = [c]
            self.cells[c.r][c.c].has_been_added_to_work_list = True

            while work_list:
                coord = work_list.pop()
                cell = self.cells[coord.r][coord.c]
                cell.has_been_flattened = True
                cell.final_room_number = flattened_value
                cell.display_c = CH_BULLET

                for dr in range(-1, 2):
                    for dc in range(-1, 2):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = coord.r + dr, coord.c + dc
                        if not (0 <= nr < BOARD_ROWS and 0 <= nc < BOARD_COLUMNS):
                            continue
                        nb = self.cells[nr][nc]
                        if nb.has_been_added_to_work_list:
                            continue
                        if nb.base_type != CellBaseType.ROOM:
                            continue
                        if nb.has_been_flattened:
                            continue
                        nb.has_been_added_to_work_list = True
                        work_list.append(Coordinate(nr, nc))

    # -- torch lighting ------------------------------------------------

    def _place_torches(self) -> None:
        """Place wall torches in rooms and compute lit cells.

        Each room has a chance to receive 1-3 torches on random
        interior wall positions.  After placement, cells within
        TORCH_LIGHT_RADIUS of any torch are marked lit (subject to
        line of sight from the torch -- light doesn't pass through
        walls or closed doors).  Overlapping torches can illuminate
        an entire room.
        """
        for rm in self.rooms:
            if self.rng.randint(1, 100) > TORCH_ROOM_CHANCE:
                continue  # This room stays dark.

            candidates: list[Coordinate] = self._find_torch_positions(rm)
            if not candidates:
                continue

            count: int = self.rng.randint(
                1, min(MAX_TORCHES_PER_ROOM, len(candidates))
            )
            self.rng.shuffle(candidates)
            for pos in candidates[:count]:
                self.torches.append(pos)

        self._compute_lighting()

    def _find_torch_positions(self, rm: Room) -> list[Coordinate]:
        """Find wall cells around a room suitable for torch placement.

        Torches go on wall cells that are adjacent to the room's
        interior floor.  Door cells are skipped.
        """
        positions: list[Coordinate] = []

        # Top and bottom walls.
        for c in range(rm.tl.c, rm.br.c):
            for r in (rm.tl.r - 1, rm.br.r):
                if 0 <= r < BOARD_ROWS:
                    if self.cells[r][c].base_type == CellBaseType.WALL:
                        positions.append(Coordinate(r, c))

        # Left and right walls.
        for r in range(rm.tl.r, rm.br.r):
            for c in (rm.tl.c - 1, rm.br.c):
                if 0 <= c < BOARD_COLUMNS:
                    if self.cells[r][c].base_type == CellBaseType.WALL:
                        positions.append(Coordinate(r, c))

        return positions

    def _compute_lighting(self) -> None:
        """Mark cells within torch radius as lit.

        Uses a bounding box per torch for efficiency.  Light respects
        LOS from the torch position (via _torch_los, which skips the
        wall the torch is mounted on).
        """
        for torch_pos in self.torches:
            # Tag the torch's own wall cell as lit so it renders.
            self.cells[torch_pos.r][torch_pos.c].lit = True

            min_r: int = max(0, int(torch_pos.r - TORCH_LIGHT_RADIUS) - 1)
            max_r: int = min(BOARD_ROWS,
                             int(torch_pos.r + TORCH_LIGHT_RADIUS) + 2)
            min_c: int = max(0, int(torch_pos.c - TORCH_LIGHT_RADIUS) - 1)
            max_c: int = min(BOARD_COLUMNS,
                             int(torch_pos.c + TORCH_LIGHT_RADIUS) + 2)

            for r in range(min_r, max_r):
                for c in range(min_c, max_c):
                    cell = self.cells[r][c]
                    if cell.base_type == CellBaseType.EMPTY:
                        continue
                    coord = Coordinate(r, c)
                    if coord.distance(torch_pos) > TORCH_LIGHT_RADIUS:
                        continue
                    if self._torch_los(torch_pos, coord):
                        cell.lit = True

    def _torch_los(self, torch_pos: Coordinate,
                   target: Coordinate) -> bool:
        """Line of sight from a wall-mounted torch to *target*.

        Similar to line_of_sight but skips the torch's own wall cell.
        Integer truncation in Coordinate.lerp causes small parameter
        values to still return the origin cell, so we explicitly skip
        any ray step that lands on torch_pos -- the wall the torch is
        mounted on must not block its own light.
        """
        dist: float = torch_pos.distance(target)
        if dist <= 1.0:
            return True
        delta: float = 1.0 / (dist + 1.0)
        t: float = delta
        while t < 1.0:
            s = torch_pos.lerp(target, t)
            # Skip any ray step still on the torch's own wall cell.
            if s.r == torch_pos.r and s.c == torch_pos.c:
                t += delta
                continue
            cell = self.cells[s.r][s.c]
            door_blocks: bool = (
                cell.base_type == CellBaseType.DOOR
                and cell.door_state not in (DoorState.DOOR_OPEN,
                                            DoorState.DOOR_MISSING)
            )
            if (cell.base_type in (CellBaseType.EMPTY, CellBaseType.WALL)
                    or door_blocks):
                return False
            t += delta
        return True

    # -- stairs --------------------------------------------------------

    def _place_stairs(self) -> None:
        """Place up and down staircases in distinct rooms."""
        assert len(self.rooms) > 1
        indices = list(range(len(self.rooms)))
        self.rng.shuffle(indices)

        self.upstairs = self._get_good_stair_location(self.rooms[indices[0]])
        cell_up = self.cells[self.upstairs.r][self.upstairs.c]
        cell_up.display_c = cell_up.original_c = UP_STAIRS

        self.downstairs = self._get_good_stair_location(self.rooms[indices[1]])
        cell_dn = self.cells[self.downstairs.r][self.downstairs.c]
        cell_dn.display_c = cell_dn.original_c = DOWN_STAIRS
        assert self.upstairs != self.downstairs

    def _get_good_stair_location(self, room: Room) -> Coordinate:
        """Pick a non-stair floor tile near a room's centroid."""
        retval = room.get_centroid()
        while True:
            retval.c += self.rng.randint(-1, 1)
            retval.r += self.rng.randint(-1, 1)
            if not self.is_a_stairway(retval):
                break
        return retval

    # -- goodies -------------------------------------------------------

    # Percent chance a room contains a spellbook.  Spellbooks are
    # uncommon — finding one is a meaningful event.
    SPELLBOOK_ROOM_CHANCE: int = 15

    # Chance a room gets a food scrap (attracts rats).
    FOOD_ROOM_CHANCE: int = 40

    # Chance a room gets a pile of rocks — cheap ranged ammunition.
    ROCK_ROOM_CHANCE: int = 60

    def _place_goodies(self, guarantee_fire: bool = False) -> None:
        """Seed rooms with items.  Spellbooks are rare; food is common.

        When *guarantee_fire* is True (level 1), at least one room
        gets a fire spellbook so the player can learn magic early.
        Food scraps are scattered to attract rats and give the player
        bait material.  Rocks are common — every other room or so —
        so the player has a reliable supply of cheap ranged ammo.
        """
        from game.magic import MagicSchool
        from game.items import Food, FOOD_KINDS, Rock
        schools: list[MagicSchool] = list(MagicSchool)
        placed_fire: bool = False
        for rm in self.rooms:
            c = rm.get_centroid()
            if self.is_a_stairway(c):
                continue
            if not placed_fire and guarantee_fire:
                self.add_goodie(c, Spellbook(MagicSchool.FIRE))
                placed_fire = True
                continue
            if self.rng.randint(1, 100) <= self.SPELLBOOK_ROOM_CHANCE:
                school: MagicSchool = self.rng.choice(schools)
                self.add_goodie(c, Spellbook(school))
            # Food scraps — placed at a random floor cell in the room.
            if self.rng.randint(1, 100) <= self.FOOD_ROOM_CHANCE:
                food_name, food_wt = self.rng.choice(FOOD_KINDS)
                food_pos: Coordinate = rm.random_interior_pos(self.rng)
                if not self.is_a_stairway(food_pos):
                    self.add_goodie(food_pos, Food(food_name, food_wt))
            # Rocks — piles of 2-5 land at a random floor cell.
            if self.rng.randint(1, 100) <= self.ROCK_ROOM_CHANCE:
                rock_pos: Coordinate = rm.random_interior_pos(self.rng)
                if not self.is_a_stairway(rock_pos):
                    pile = self.rng.randint(2, 5)
                    self.add_goodie(rock_pos, Rock(count=pile))
