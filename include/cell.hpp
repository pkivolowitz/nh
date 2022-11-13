#pragma once
#include <cinttypes>

enum CellBaseType {
	EMPTY,
	ROOM,
	CORRIDOR,
	WALL
};

static const int32_t DOWN_STAIRS = '>';
static const int32_t UP_STAIRS = '<';

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
	bool is_lit;
	bool is_known;
};
