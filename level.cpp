#include <iostream>
#include <fstream>
#include <cassert>

#include "level.hpp"
#include "logging.hpp"
#include "coordinate.hpp"

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

bool Level::Initialize(Presentation * p) {
	lines = p->DRAWABLE_LINES;
	cols = p->DRAWABLE_COLS;
	LOGMESSAGE("lines: " << lines << " columns: " << cols);
	bool retval = true;
	cells.resize(lines * cols);
	for (auto & c : cells) {
		c = new Rock();
	}
	for (int room_number = 0; room_number < 9; room_number++) {
	//	Coordinate br(rand() % )
	}
	RETURNING(retval);	
	return retval;
}

void Level::Replace(int l, int c, CellPtr cell) {
	//LOGMESSAGE("line: " << l << " col: " << c);
	int o = Offset(l, c);
	if (cells.at(o) != nullptr) {
		delete cells.at(o);
	}
	cells.at(o) = cell;
}

int Level::Offset(int l, int c) {
	return l * cols + c;
}

void Level::Render(Presentation * p) {
	CalculateVisibility();
	for (int l = 0; l < lines; l++) {
		wmove(stdscr, l + p->TOP_DRAWABLE_LINE, p->LEFT_DRAWABLE_COL);
		for (int c = 0; c < cols; c++) {
			//LOGMESSAGE("line: " << l << " column: " << c);
			p->AddCh((cells.at(Offset(l, c))->IsVisible()) ? cells.at(Offset(l, c))->Symbol() : ' ');
		}
	}
}

void Level::CalculateVisibility() {
	for (int l = 0; l < lines; l++) {
		for (int c = 0; c < cols; c++) {
			cells.at(Offset(l, c))->SetVisibility(true);
		}
	}
}

// -------------------------------------------------------------------------- //

const char * Cell::base_type_symbols = " #.";

Cell::Cell() {
	//ENTERING();
	flags.passable = false;
	flags.door = DOOR_NOT;
	flags.blocks_line_of_sight = true;
}

Cell::~Cell() {
	//ENTERING();
}

char Cell::Symbol() {
	char retval = fl.Top();
	if (retval == '\0')
		retval = base_type_symbols[(int) bt];
	return retval;
}

void Cell::Push(ItemPtr p) {
	assert(p != nullptr);
	fl.Push(p);
}

ItemPtr Cell::Pop() {
	return nullptr;
}

bool Cell::IsVisible() {
	return flags.is_visible;
}

void Cell::SetVisibility(bool f) {
	flags.is_visible = f;
}

Rock::Rock() {
	//ENTERING();
	bt = BaseType::ROCK;
}

Rock::~Rock() {
	//ENTERING();
}

Hallway::Hallway() {
	//ENTERING();
	bt = BaseType::HALLWAY;
}

Hallway::~Hallway() {
	//ENTERING();
}

Floor::Floor() {
	//ENTERING();
	bt = BaseType::FLOOR;
}

Floor::~Floor() {
	//ENTERING();
}

