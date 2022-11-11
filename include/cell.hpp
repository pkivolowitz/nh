#pragma once
#include <cinttypes>

enum CellBaseType {
	EMPTY,
	ROOM,
	CORRIDOR
};

struct Cell {
	Cell();
	CellBaseType base_type;
	int32_t c;
	int32_t display_c;
	bool has_been_flattened;
};
