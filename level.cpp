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
	LOGMESSAGE("lines: " << lines << " columns: " << cols);
	bool retval = true;
	this->lines = lines;
	this->cols = cols;

	cells.resize(lines * cols);
	for (auto & c : cells) {
		c = new Rock();
	}
	RETURNING(retval);	
	return retval;
}

int Level::Offset(int l, int c) {
	return l * lines + c;
}

void Level::Render(Presentation * p) {
	CalculateVisibility();
	for (int l = 0; l < lines; l++) {
		wmove(stdscr, l + p->TOP_DRAWABLE_LINE, p->LEFT_DRAWABLE_COL);
		for (int c = 0; c < cols; c++) {
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

Cell::Cell() {
	ENTERING();
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

bool Cell::IsVisible() {
	return flags.is_visible;
}

void Cell::SetVisibility(bool f) {
	flags.is_visible = f;
}

Rock::Rock() {
	ENTERING();
	bt = BaseType::ROCK;
}

