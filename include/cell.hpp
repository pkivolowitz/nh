#pragma once
#include <cinttypes>

enum CellBaseType {
	EMPTY,
	ROOM,
	CORRIDOR
};

static const int32_t DOWN_STAIRS = '>';
static const int32_t UP_STAIRS = '<';

struct Cell {
	Cell();
	CellBaseType base_type;
	int32_t c;
	int32_t display_c;
	bool has_been_flattened;
	bool has_been_added_to_work_list;
};
