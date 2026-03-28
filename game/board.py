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
)
from game.cell import Cell, CellBaseType, DoorState
from game.coordinate import Coordinate
from game.room import Room
from game.items import BaseItem, Spellbook
from game.drawing_support import corner_map


class Board:
    """One dungeon level.

    Construction generates the full level: rooms, walls, corridors,
    corners, doors, stairs, and floor items.
    """

    def __init__(self, rng: random.Random) -> None:
        self.rng: random.Random = rng
        self.cells: list[list[Cell]] = [
            [Cell() for _ in range(BOARD_COLUMNS)]
            for _ in range(BOARD_ROWS)
        ]
        self.rooms: list[Room] = []
        self.goodies: dict[Coordinate, list[BaseItem]] = {}
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
        """Place an item on the floor at *c*."""
        self.goodies.setdefault(c, []).append(item)

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
    # Door interaction
    # ------------------------------------------------------------------

    def try_open_door(self, c: Coordinate) -> str:
        """Attempt to open the door at *c*.  Returns a message string."""
        if not (0 <= c.r < BOARD_ROWS and 0 <= c.c < BOARD_COLUMNS):
            return "There is nothing there to open."
        cell = self.cells[c.r][c.c]
        if cell.base_type != CellBaseType.DOOR:
            return "There is nothing there to open."
        if cell.door_state in (DoorState.DOOR_OPEN, DoorState.DOOR_MISSING):
            return "This door is already open."
        if cell.door_state == DoorState.DOOR_LOCKED:
            return "This door is locked."
        if cell.door_state == DoorState.DOOR_STUCK:
            return "The door is stuck!"
        if cell.door_state == DoorState.DOOR_CLOSED:
            cell.door_state = DoorState.DOOR_OPEN
            self._update_door_display(c.r, c.c)
            return "You open the door."
        return ""

    def try_kick_door(self, c: Coordinate) -> str:
        """Kick the door at *c*.  Can force stuck and locked doors.

        Returns a message string.  Success is probabilistic.
        """
        if not (0 <= c.r < BOARD_ROWS and 0 <= c.c < BOARD_COLUMNS):
            return "You kick at nothing."
        cell = self.cells[c.r][c.c]
        if cell.base_type != CellBaseType.DOOR:
            return "You kick at nothing."
        if cell.door_state in (DoorState.DOOR_OPEN, DoorState.DOOR_MISSING):
            return "That door is already open."
        # Kick chances: stuck 40%, locked 25%, closed 80%.
        chances = {
            DoorState.DOOR_STUCK: 40,
            DoorState.DOOR_LOCKED: 25,
            DoorState.DOOR_CLOSED: 80,
        }
        chance = chances.get(cell.door_state, 0)
        if self.rng.randint(1, 100) <= chance:
            cell.door_state = DoorState.DOOR_OPEN
            self._update_door_display(c.r, c.c)
            return "You kick the door open!"
        return "The door resists."

    def try_close_door(self, c: Coordinate) -> str:
        """Attempt to close the door at *c*.  Returns a message string."""
        if not (0 <= c.r < BOARD_ROWS and 0 <= c.c < BOARD_COLUMNS):
            return "There is nothing there to close."
        cell = self.cells[c.r][c.c]
        if cell.base_type != CellBaseType.DOOR:
            return "There is nothing there to close."
        if cell.door_state in (DoorState.DOOR_CLOSED, DoorState.DOOR_LOCKED,
                               DoorState.DOOR_STUCK):
            return "This door is already closed."
        if cell.door_state == DoorState.DOOR_MISSING:
            return "There is no door there to close."
        if cell.door_state == DoorState.DOOR_OPEN:
            cell.door_state = DoorState.DOOR_CLOSED
            self._update_door_display(c.r, c.c)
            return "You close the door."
        return ""

    # ------------------------------------------------------------------
    # Visibility (curses-free)
    # ------------------------------------------------------------------

    def update_visibility(self, pos: Coordinate,
                          tr: float = DEFAULT_TORCH_RADIUS) -> None:
        """Mark cells within torch range and LOS as known.

        Called by the engine after every action so that both the
        renderer and headless AI see consistent ``is_known`` flags.
        """
        for r in range(BOARD_ROWS):
            for c in range(BOARD_COLUMNS):
                cell = self.cells[r][c]
                if cell.base_type == CellBaseType.EMPTY:
                    continue
                if cell.is_known:
                    continue
                coord = Coordinate(r, c)
                if coord.distance(pos) >= tr:
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
        self._place_stairs()
        self._place_goodies()

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

        # Horizontal leg.
        if src.c != dst.c:
            dc = 1 if src.c < dst.c else -1
            r = src.r
            c = src.c
            while c != dst.c:
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

        # Vertical leg.
        if src.r != dst.r:
            dr = 1 if src.r < dst.r else -1
            c = dst.c
            r = src.r
            while r != dst.r:
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
                else:
                    cell.door_state = DoorState.DOOR_LOCKED

                self._update_door_display(r, c)

    def _update_door_display(self, r: int, c: int) -> None:
        """Refresh a door cell's display character after state change."""
        cell = self.cells[r][c]
        if cell.door_state == DoorState.DOOR_MISSING:
            cell.display_c = ord("#")
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

    def _place_goodies(self) -> None:
        """Seed each room with a sample item at its centroid."""
        for rm in self.rooms:
            c = rm.get_centroid()
            if self.is_a_stairway(c):
                continue
            self.add_goodie(c, Spellbook())
