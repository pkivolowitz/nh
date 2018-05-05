#pragma once
#include <vector>
#include "floor_manager.hpp"

/*	CellFlags describes attributes of cells for which there can be only one. 
	For example:
		- is what is in this cell make it *impossible* to traverse?
		- there can be at most one door.
		- does this cell block line of sight?
*/

struct CellFlags {
	unsigned char passable : 1;
	unsigned char door : 2;
	unsigned char blocks_line_of_sight : 1;
};

enum {
	DOOR_NOT,
	DOOR_OPEN,
	DOOR_CLOSED
};

class Cell {
	public:
		Cell();
		char Symbol();
		void Push(ItemPtr);
		ItemPtr Pop();

	private:
		CellFlags flags;
		FloorManager fl;
};

class Level {
	public:
		Level();
		~Level();
		bool Initialize(int lines, int cols);

	private:
		std::vector<Cell *> cells;
		int lines;
		int cols;
};
