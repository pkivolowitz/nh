// Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

#pragma once
#include <cinttypes>

enum CellBaseType {
	EMPTY,
	ROOM,
	CORRIDOR,
	WALL,
	DOOR
};

// Door states. DOOR_NONE is 0 so memset-initialized cells default
// to "not a door." The visual difference between LOCKED, STUCK, and
// plain CLOSED is communicated through gameplay, not rendering — all
// three show '+'.
enum DoorState {
	DOOR_NONE = 0,		// Not a door (default from memset).
	DOOR_MISSING,		// Archway — no physical door, always passable.
	DOOR_OPEN,			// Open door — passable, doesn't block LOS.
	DOOR_CLOSED,		// Closed door — blocks movement and LOS.
	DOOR_LOCKED,		// Locked and closed — must unlock or kick.
	DOOR_STUCK,			// Stuck and closed — must force open or kick.
};

static const int32_t DOWN_STAIRS = '>';
static const int32_t UP_STAIRS = '<';

// Symbol for closed/locked/stuck doors. '+' is also used for
// spellbooks but context disambiguates (doors are on walls,
// spellbooks are on floors).
static const int32_t DOOR_CLOSED_SYM = '+';

/*	Cells in "lit" rooms are also marked lit. This enables the walls
	in lit rooms to be marked lit which otherwise they could not be.
*/
struct Cell {
	Cell();
	CellBaseType base_type;
	int32_t original_c;
	int32_t display_c;
	int32_t final_room_number;
	bool has_been_flattened;
	bool has_been_added_to_work_list;
	bool is_known;

	// Door fields — only meaningful when base_type == DOOR.
	DoorState door_state;
	// true = door is on a horizontal wall (you walk vertically through it).
	// false = door is on a vertical wall (you walk horizontally through it).
	bool door_horizontal;
};
