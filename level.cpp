#include <iostream>
#include <fstream>

#include "level.hpp"
#include "logging.hpp"

using namespace std;

Level::Level() {
}

Level::~Level() {
	ENTERING();
	for (auto & p : cells) {
		if (p != nullptr)
			delete p;
	}
	LEAVING();
}

bool Level::Initialize(int lines, int cols) {
	ENTERING();
	bool retval = true;
	this->lines = lines;
	this->cols = cols;

	cells.resize(lines * cols);
	for (auto & c : cells) {
		c = new Cell();
	}
	RETURNING(retval);	
	return retval;
}

Cell::Cell() {
	flags.passable = false;
	flags.door = DOOR_NOT;
	flags.blocks_line_of_sight = true;
}

char Cell::Symbol() {
	return fl.Top();
}

void Cell::Push(ItemPtr p) {
	assert(p != nullptr);
	fl.Push(p);
}

ItemPtr Cell::Pop() {
	return nullptr;
}

