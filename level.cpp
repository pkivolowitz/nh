#include <iostream>
#include <fstream>
#include <vector>
#include <cassert>
#include <cstdlib>

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
	Coordinate tl, br;
	for (int room_number = MAX_ROOMS; room_number >= 0; room_number--) {
		vector<Coordinate> v;
		CalcRoomBoundaries(tl, br);
		FillRoomBoundaries(tl, br, v, room_number);
		if (room_number == MAX_ROOMS)
			continue;
		FlattenRoom(v, room_number);
	}
	RETURNING(retval);	
	return retval;
}

void Level::FlattenRoom(vector<Coordinate> & v, int room_number) {
	auto ci = v.begin();
	while (ci != v.end()) {
		CheckFloor(*ci, v, room_number);
		ci++;
	}
}

void Level::CheckFloor(Coordinate & center, vector<Coordinate> & v, int room_number) {
	for (int l = center.l - 1; l <= center.l + 1; l++) {
		if (l < 0 || l >= lines)
			continue;
		for (int c = center.c - 1; c <= center.c + 1; c++) {
			if (c < 0 || c >= cols)
				continue;
			if (c == center.c && l == center.l)
				continue;
			Floor * cp = (Floor *) cells.at(Offset(l, c));
			if (cp->BT() == BaseType::FLOOR && cp->GetRoomNumber() > room_number) {
				cp->SetRoomNumber(room_number);
				v.push_back(Coordinate(l, c));
			}
		}
	}
}

void Level::FillRoomBoundaries(Coordinate & tl, Coordinate & br, vector<Coordinate> & v, int room_number) {
	for (int l = tl.l; l <= br.l; l++) {
		for (int c = tl.c; c <= br.c; c++) {
			v.push_back(Coordinate(l, c));
			Replace(l, c, new Floor(room_number));
		}
	}
}

void Level::CalcRoomBoundaries(Coordinate & tl, Coordinate & br) {
	tl = Coordinate(rand() % (lines - 3), rand() % (cols - 3));
	Coordinate dims(rand() % 5 + 2, rand() % 10 + 2);
	br = tl + dims;
	br.Clip(lines, cols);
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
			CellPtr cp = cells.at(Offset(l, c));
			char s = (cp->IsVisible()) ? cp->Symbol() : ' ';
			if (cp->BT() == BaseType::FLOOR) s = (char) (((Floor *) cp)->GetRoomNumber() + '0');
			p->AddCh(s);
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

BaseType Cell::BT() {
	return bt;
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
	room_number = 0;
}

Floor::Floor(int rm) {
	//ENTERING();
	bt = BaseType::FLOOR;
	room_number = rm;
}

void Floor::SetRoomNumber(int rm) {
	room_number = rm;
}

int Floor::GetRoomNumber() {
	return room_number;
}

Floor::~Floor() {
	//ENTERING();
}

