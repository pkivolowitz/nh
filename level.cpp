#include <iostream>
#include <fstream>

#include "level.hpp"

using namespace std;

extern ofstream log;

int Level::MAX_COLS = 128;
int Level::MAX_LINES = 128;

Level::Level() {
	log << __FILE__ << " " << __FUNCTION__ << " " << __LINE__ << endl;	
}

bool Level::Initialize(int lines, int cols) {
	log << __FILE__ << " " << __FUNCTION__ << " " << __LINE__ << endl;
	assert(lines > 0 && lines < MAX_LINES);
	assert(cols > 0 && cols < MAX_COLS);

	this->lines = lines;
	this->cols = cols;

	// The following adds empty cells to a screen sized array.
	cells.resize(lines);
	for (int l = 0; l < lines; l++)
		cells.at(l).resize(cols);

	
	log << __FILE__ << " " << __FUNCTION__ << " " << __LINE__ << endl;
	return true;
}

Cell::Cell() {
	flags.passable = 0;
	flags.door = NOT_A_DOOR;
}
