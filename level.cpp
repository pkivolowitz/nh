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
		CalcRoomBoundaries(tl, br, p);
		FillRoomBoundaries(tl, br, v, room_number);
		if (room_number == MAX_ROOMS)
			continue;
		FlattenRoom(v, room_number);
	}
	RETURNING(retval);	
	return retval;
}

/* 	FlattenRoom - iterates through the cells in the vector v. These cells match the
	current (minimal) room number. Each cell's neighbors are examined - if they are
	a floor unit as well but with a larger room number, that cell is relabeled and
	added to the vector.
*/ 
void Level::FlattenRoom(vector<Coordinate> & v, int room_number) {
	//ENTERING();
	unsigned int index = 0;
	while (index < v.size()) {
		CheckFloor(v.at(index), v, room_number);
		index++;
	}
	//LEAVING();
}

/*	CheckFloor - Like a convolution kernel, this function checks a cell's 8 neighbors
	to see if they are a) Floors and b) from a room with a higher index than the
	current room. Rooms are defined in decreasing order so that this makes sense. The
	algorithm isn't optimal, but with small arrays (24x80) this is irrelevant.
*/
void Level::CheckFloor(Coordinate & center, vector<Coordinate> & v, int room_number) {
	//ENTERING();
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
	//LEAVING();
}

/*	FillRoomBoundaries - fills each cell with a Floor within the rectangle specified by tl and br.
	Each cell coordinate is added to a vector which is used to flood fill the room number in the
	step of level creation. Note that rooms are created with descending IDs.
*/
void Level::FillRoomBoundaries(Coordinate & tl, Coordinate & br, vector<Coordinate> & v, int room_number) {
	//ENTERING();
	for (int l = tl.l; l <= br.l; l++) {
		for (int c = tl.c; c <= br.c; c++) {
			v.push_back(Coordinate(l, c));
			Replace(l, c, new Floor(room_number));
		}
	}
	//LEAVING();
}

void Level::CalcRoomBoundaries(Coordinate & tl, Coordinate & br, Presentation * p) {
	assert(p != nullptr);
	tl = Coordinate(rand() % (lines - p->COMMAND_LINES - p->STATUS_LINES), rand() % (cols - 1 - MIN_ROOM_WIDTH));
	Coordinate dims(rand() % MAX_ROOM_HEIGHT_RAND + MIN_ROOM_HEIGHT, rand() % MAX_ROOM_WIDTH_RAND + MIN_ROOM_WIDTH);
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

