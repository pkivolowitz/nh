// Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

#include <fstream>
#include <iomanip>
#include <iostream>
#include <ncurses.h>
#include <random>
#include <string>
#include <sstream>
#include <float.h>

#include "board.hpp"
#include "drawing_support.hpp"
#include "colors.hpp"

using namespace std;

extern ofstream my_log;
extern bool show_floor;

static GameTime gt;

// Build a fresh board by clearing state and generating a level.
Board::Board() {
	Clear();
	Create();
}

extern bool operator<(const Coordinate &l, const Coordinate &r);

// Draw the current clock into the upper-right corner of the map window.
void Board::UpdateTime() {
	string current_time = gt.GetCurrentTime();
	mvwaddstr(win, 0, BOARD_COLUMNS - 8, current_time.c_str());
	// Caller is responsible for wrefresh.
}

// Report whether a coordinate can be stepped on right now.
bool Board::IsNavigable(Coordinate & c) {
	CellBaseType bt = cells[c.r][c.c].base_type;
	if (bt == ROOM || bt == CORRIDOR) return true;
	if (bt == DOOR) return IsDoorPassable(c);
	return false;
}

// Report whether a coordinate contains a door cell.
bool Board::IsDoor(Coordinate & c) {
	return cells[c.r][c.c].base_type == DOOR;
}

// Report whether the door at a coordinate currently allows movement.
bool Board::IsDoorPassable(Coordinate & c) {
	DoorState ds = cells[c.r][c.c].door_state;
	return ds == DOOR_MISSING || ds == DOOR_OPEN;
}

/*	Clear() - This function zeros out the Board data structure making
	ready for the next newly created level. Note that the use of memset
	means that if Cell someday has need of a destructure, this code will
	need refactoring.
*/
void Board::Clear() {
	memset(cells, 0, BOARD_ROWS * BOARD_COLUMNS * sizeof(Cell));
	rooms.clear();
}

/*	FindRowsToAvoid
	FindColsToAvoid

	Called prior to laying out corridors, this function builds an ivec
	which contains the columns and rows for which corridors should be
	avoided. The reason is to avoid having a corridor run along the
	edge of a room. While this would make some sense as being an open
	cavern, the appearence is ugly.
*/
void Board::FindRowsToAvoid(ivec &r_avoid) {
	for (int32_t r = 0; r < BOARD_ROWS; r++) {
		for (int32_t c = 0; c < BOARD_COLUMNS; c++) {
			if (cells[r][c].original_c == ACS_HLINE) {
				r_avoid.push_back(r);
				break;
			}
		}
	}
	if (false and my_log.is_open()) {
		my_log << "Rows to avoid: ";
		for (auto i : r_avoid)
			my_log << i << " ";
		my_log << endl;
	}
}

void Board::FindColsToAvoid(ivec &c_avoid) {
	for (int32_t c = 0; c < BOARD_COLUMNS; c++) {
		for (int32_t r = 0; r < BOARD_ROWS; r++) {
			if (cells[r][c].original_c == ACS_VLINE) {
				c_avoid.push_back(c);
				break;
			}
		}
	}
	if (false and my_log.is_open()) {
		my_log << "Cols to avoid: ";
		for (auto i : c_avoid)
			my_log << i << " ";
		my_log << endl;
	}
}

/*	There is a problem here in that the bad rows and bad columns
	calculation is across the whole board. I see a situation where
	there is no way out of a room horizontally when you look at the
	whole board but there is if you consider only the part of the
	board from src to dst. This means a global calculation is no
	good and instead a region-of-interest type calculation is more
	appropriate.
*/

/*	FindGoodCoordinates - this function goes through extra effort to
	determine a position within the given room from which to start or
	end a corridor. The extra work is due to wanting to be able to
	choose any spot in the room that does not lie in a row or column
	which would cause a corridor to run along the edge of a room.
*/
void Board::FindGCoords(ivec &br, ivec &bc, Room &r, Coordinate &coord) {
	ivec rows_in_room;
	ivec cols_in_room;

	for (int32_t i = r.tl.c; i < r.br.c; i++)
		cols_in_room.push_back(i);
	for (int32_t i = r.tl.r; i < r.br.r; i++)
		rows_in_room.push_back(i);

	shuffle(cols_in_room.begin(), cols_in_room.end(), default_random_engine(rand()));
	shuffle(rows_in_room.begin(), rows_in_room.end(), default_random_engine(rand()));

	coord.c = coord.r = -1;

	// Refactor this someday to remove duplicated code.
	for (int32_t i : cols_in_room) {
		auto it = find(bc.begin(), bc.end(), i);
		if (it == bc.end()) {
			coord.c = i;
			break;
		}
	}

	for (int32_t i : rows_in_room) {
		auto it = find(br.begin(), br.end(), i);
		if (it == br.end()) {
			coord.r = i;
			break;
		}
	}
	if (false and my_log.is_open()) {
		my_log << "Room: " << r.room_number << " ";
		my_log << coord.r << " " << coord.c << endl;
	}
}

// Connect generated rooms in sequence using corridor endpoints inside each room.
void Board::PlaceCorridors() {
	ivec needs_plan_b;
	ivec bc; // bad_columns
	ivec br; // bad_rows

	FindColsToAvoid(bc);
	FindRowsToAvoid(br);
	if (false and my_log.is_open()) {
		my_log << "ColsToAvoid.size() " << bc.size() << endl;
		my_log << "RowsToAvoid.size() " << br.size() << endl;
	}

	vector<Coordinate> key_points;
	for (auto &r : rooms) {
		Coordinate coord;
		FindGCoords(br, bc, r, coord);
		if (coord.c < 0 || coord.r < 0) {
			needs_plan_b.push_back(r.room_number);
			continue;
		}
		key_points.push_back(coord);
	}
	if (false and my_log.is_open()) {
		my_log << "KeyPoint.size() " << key_points.size() << endl;
	}

	assert(key_points.size() > 0);
	for (uint32_t index = 0; index < key_points.size() - 1; index++) {
		Coordinate &src = key_points[index];
		Coordinate &dst = key_points[index + 1];
		LayCorridor(src, dst);
	}

	for (auto r : needs_plan_b) {
		PlanBForCooridors(r);
	}
}

// Convert the targeted coordinate into corridor floor.
void Board::MakeCorridor(Coordinate & c) {
	MakeCorridor(cells[c.r][c.c]);
}

// Convert a single cell into corridor floor and tag wall breakpoints for door placement.
void Board::MakeCorridor(Cell & c) {
	if (isdigit(c.original_c))
		return;
	// If this cell was a wall, mark it as a door candidate.
	// PlaceDoors() will filter by adjacency and randomize states.
	bool was_wall = (c.base_type == WALL);
	c.display_c = c.original_c = '#';
	c.base_type = CORRIDOR;
	c.final_room_number = -1;
	if (was_wall) {
		c.door_state = DOOR_CLOSED;		// Placeholder for PlaceDoors.
	}
}

// Carve an L-shaped corridor between two selected room points.
void Board::LayCorridor(Coordinate & src, Coordinate & dst) {
	vector<Coordinate> seeds;

	if (src.c != dst.c) {
		int32_t dc = (src.c < dst.c) ? 1 : -1;
		int32_t r = src.r;
		for (int32_t c = src.c; c != dst.c; c += dc) {
			if (c < 0 or c >= BOARD_COLUMNS)
				break;
			MakeCorridor(cells[r][c]);
			if (RR(1,100) < 3)
				seeds.push_back(Coordinate(r,c));
		}
	}
	for (Coordinate & c : seeds) {
		if (BuildCornerKey(c) == "         ") {
			int32_t delta_r = (RR() & 1) ? 1 : -1;
			int32_t nspaces = RR(1, 3);
			while (nspaces-- > 0) {
				c.r += delta_r;
				if (c.r < 0 or c.r >= BOARD_ROWS)
					break;
				if (!IsEmpty(c))
					break;
				MakeCorridor(c);
			}
		}
	}
	if (src.r != dst.r) {
		int32_t dr = (src.r < dst.r) ? 1 : -1;
		int32_t c = dst.c;
		for (int32_t r = src.r; r != dst.r; r += dr) {
			if (r < 0 or r >= BOARD_ROWS)
				break;
			MakeCorridor(cells[r][c]);
		}
	}
}

/*	This function samples the 3x3 neighborhood surrounding the current
	position, turning it into a nine byte characterization. This, in
	turn, is used as the key into a map containing the special cases
	for rendering the board. This work is due to my desire to use the
	line drawing character set. NetHack and rogue do not do this.

	And, if they did, their rooms are rectangles and do not overlap.
	This makes their job so much easier as only the four corners need
	be handled.
*/
string Board::BuildCornerKey(int32_t r, int32_t c) {
	string retval;

	for (int32_t dr = -1; dr <= 1; dr++) {
		for (int32_t dc = -1; dc <= 1; dc++) {
			int32_t C = dc + c;
			int32_t R = dr + r;
			if (R < 0 or R >= BOARD_ROWS)
				retval.push_back(' ');
			else if (C < 0 or C >= BOARD_COLUMNS)
				retval.push_back(' ');
			else if (!cells[R][C].original_c)
				retval.push_back(' ');
			else if (isdigit(cells[R][C].original_c))
				retval.push_back('F');
			else if (cells[R][C].original_c == ACS_HLINE)
				retval.push_back('H');
			else if (cells[R][C].original_c == ACS_VLINE)
				retval.push_back('V');
			else {
				retval.push_back(' ');
			}
		}
	}

	return retval;
}

// Build the neighborhood key for the given coordinate overload.
string Board::BuildCornerKey(Coordinate & c) {
	return BuildCornerKey(c.r, c.c);
}

/*	PlaceCorners() - populate each cell's display_c with a special
	cased line drawing character IF needed. Otherwise, simply copy
	over the cell's c.
*/
void Board::PlaceCorners() {
	for (int32_t r = 0; r < BOARD_ROWS; r++) {
		for (int32_t c = 0; c < BOARD_COLUMNS; c++) {
			string key = BuildCornerKey(r, c);
			if (corner_map.count(key) != 0) {
				cells[r][c].display_c = corner_map[key];
			} else {
				cells[r][c].display_c = cells[r][c].original_c;
			}
		}
	}
}

/*	Fill() - an intermediate step in incrementally building the
	renderable board.
*/
// Fill every interior tile of a room with its temporary room id.
void Board::Fill(int32_t rn) {
	Room & rm = rooms[rn];
	for (int32_t r = rm.tl.r; r < rm.br.r; r++) {
		for (int32_t c = rm.tl.c; c < rm.br.c; c++) {
			assert(c > 0);
			assert(r < BOARD_ROWS);
			assert(c < BOARD_COLUMNS);
			cells[r][c].original_c = '0' + rn;
			cells[r][c].display_c = '0' + rn;
			cells[r][c].base_type = ROOM;
		}
	}
}

// Initialize a cell's type and base display character together.
inline void SetCell(Cell & cell, CellBaseType bt, int32_t c) {
	cell.base_type = bt;
	cell.original_c = c;
}

// Surround a room's filled interior with wall cells.
void Board::Enclose(int32_t rn) {
	Room & rm = rooms[rn];
	for (int32_t r = rm.tl.r; r < rm.br.r; r++) {
		assert(r < BOARD_ROWS);
		assert(rm.tl.c > 0);
		assert(rm.br.c < BOARD_COLUMNS);
		if (!cells[r][rm.tl.c - 1].original_c) {
			SetCell(cells[r][rm.tl.c - 1], WALL, ACS_VLINE);
		}
		if (!cells[r][rm.br.c].original_c) {
			SetCell(cells[r][rm.br.c], WALL, ACS_VLINE);
		}
	}
	for (int32_t c = rm.tl.c - 1; c < rm.br.c + 1; c++) {
		assert(c < BOARD_COLUMNS);
		assert(rm.tl.r > 0);
		assert(rm.br.r < BOARD_ROWS);
		if (!cells[rm.tl.r - 1][c].original_c) {
			SetCell(cells[rm.tl.r - 1][c], WALL, ACS_HLINE);
		}
		if (!cells[rm.br.r][c].original_c) {
			SetCell(cells[rm.br.r][c], WALL, ACS_HLINE);
		}
	}
}

// Add a floor item to the stack stored at the given coordinate.
void Board::AddGoodie(Coordinate c, unique_ptr<BaseItem> item) {
	auto it = goodies.find(c);
	if (it == goodies.end()) {
		vector<unique_ptr<BaseItem>> v;
		goodies.insert({c, std::move(v)});
		it = goodies.find(c);
	}
	it->second.push_back(std::move(item));
}

// Remove and return every floor item stored at the given coordinate.
vector<unique_ptr<BaseItem>> Board::RemoveGoodies(Coordinate c) {
	vector<unique_ptr<BaseItem>> retval;
	auto it = goodies.find(c);
	if (it != goodies.end()) {
		retval = std::move(it->second);
		goodies.erase(it);
	}
	return retval;
}

// Seed each room with a sample goodie at its centroid when possible.
void Board::PlaceGoodies() {
	for (auto & r : rooms) {
		Coordinate c = r.GetCentroid();
		// Don't auto-place items on stairways during generation.
		if (IsAStairway(c)) {
			if (my_log.is_open()) {
				my_log << "Avoiding adding a goodie on a stairway.\n";
			}
			continue;
		}
		AddGoodie(c, make_unique<Spellbook>());
	}
}

// Write floor-item positions to the debug log.
void Board::PrintGoodies() {
	if (!my_log.is_open())
		return;

	for (auto & it : goodies) {
		my_log << it.first.r << " " << it.first.c << " ";
		my_log << it.second.size() << endl;
	}
}

// Generate the full contents of a level from scratch.
void Board::Create() {
	extern bool no_corridors;
	int32_t room_count = RR(MIN_ROOMS, MAX_ROOMS);
	rooms.resize(room_count);
	for (uint32_t rn = 0; rn < rooms.size(); rn++) {
		rooms[rn].Initialize(rn);
		Fill(rn);
		Enclose(rn);
	}
	PlaceCorners();
	if (!no_corridors) {
		PlaceCorridors();
		PlaceDoors();
	}
	FlattenRooms();
	PlaceStairs();
	PlaceGoodies();
	PrintGoodies();
}

// Refresh a door cell's rendered glyph after changing its state.
void Board::UpdateDoorDisplay(int32_t r, int32_t c) {
	Cell & cell = cells[r][c];
	switch (cell.door_state) {
		case DOOR_MISSING:
			// Archway — render as corridor floor.
			cell.display_c = '#';
			break;
		case DOOR_OPEN:
			// Open door contrasts with the wall it sits in.
			// Vertical wall (|) → open door is '-'.
			// Horizontal wall (—) → open door is '|'.
			cell.display_c = cell.door_horizontal ? '|' : '-';
			break;
		case DOOR_CLOSED:
		case DOOR_LOCKED:
		case DOOR_STUCK:
			cell.display_c = DOOR_CLOSED_SYM;
			break;
		default:
			break;
	}
	cell.original_c = cell.display_c;
}

/*	PlaceDoors() — scan for corridor cells that were converted from
	walls (marked with door_state != DOOR_NONE by MakeCorridor). A
	valid door position must have a ROOM neighbor on one orthogonal
	axis and a non-ROOM neighbor on the other side of that axis, so
	it sits at the boundary between corridor and room.

	Door state probabilities:
		20% missing (archway, no physical door)
		30% open
		25% closed
		15% stuck (closed and stuck)
		10% locked
*/
void Board::PlaceDoors() {
	for (int32_t r = 0; r < BOARD_ROWS; r++) {
		for (int32_t c = 0; c < BOARD_COLUMNS; c++) {
			// Only process cells MakeCorridor flagged as wall-to-corridor.
			if (cells[r][c].door_state == DOOR_NONE) continue;
			if (cells[r][c].base_type != CORRIDOR) continue;

			// Check vertical axis: room above/below with non-room on
			// the opposite side means this is a door on a horizontal wall.
			bool room_above = (r > 0 && cells[r-1][c].base_type == ROOM);
			bool room_below = (r < BOARD_ROWS-1 && cells[r+1][c].base_type == ROOM);
			bool room_left  = (c > 0 && cells[r][c-1].base_type == ROOM);
			bool room_right = (c < BOARD_COLUMNS-1 && cells[r][c+1].base_type == ROOM);

			bool vert_door = (room_above && !room_below) ||
							 (room_below && !room_above);
			bool horiz_door = (room_left && !room_right) ||
							  (room_right && !room_left);

			if (!vert_door && !horiz_door) {
				// Not a boundary position — clear the placeholder.
				cells[r][c].door_state = DOOR_NONE;
				continue;
			}

			cells[r][c].base_type = DOOR;
			// door_horizontal = true when door is on a horizontal wall
			// (room above or below, you walk vertically through it).
			cells[r][c].door_horizontal = vert_door;

			// Randomize door state.
			int32_t roll = RR(1, 100);
			if (roll <= 20) {
				cells[r][c].door_state = DOOR_MISSING;
			} else if (roll <= 50) {
				cells[r][c].door_state = DOOR_OPEN;
			} else if (roll <= 75) {
				cells[r][c].door_state = DOOR_CLOSED;
			} else if (roll <= 90) {
				cells[r][c].door_state = DOOR_STUCK;
			} else {
				cells[r][c].door_state = DOOR_LOCKED;
			}

			UpdateDoorDisplay(r, c);
		}
	}
}

// Attempt to open the door at the requested coordinate.
string Board::TryOpenDoor(Coordinate & c) {
	if (c.r < 0 || c.r >= BOARD_ROWS || c.c < 0 || c.c >= BOARD_COLUMNS)
		return "There is nothing there to open.";

	Cell & cell = cells[c.r][c.c];
	if (cell.base_type != DOOR)
		return "There is nothing there to open.";

	switch (cell.door_state) {
		case DOOR_OPEN:
		case DOOR_MISSING:
			return "This door is already open.";
		case DOOR_LOCKED:
			return "This door is locked.";
		case DOOR_STUCK:
			return "The door is stuck!";
		case DOOR_CLOSED:
			cell.door_state = DOOR_OPEN;
			UpdateDoorDisplay(c.r, c.c);
			return "You open the door.";
		default:
			return "";
	}
}

// Attempt to close the door at the requested coordinate.
string Board::TryCloseDoor(Coordinate & c) {
	if (c.r < 0 || c.r >= BOARD_ROWS || c.c < 0 || c.c >= BOARD_COLUMNS)
		return "There is nothing there to close.";

	Cell & cell = cells[c.r][c.c];
	if (cell.base_type != DOOR)
		return "There is nothing there to close.";

	switch (cell.door_state) {
		case DOOR_CLOSED:
		case DOOR_LOCKED:
		case DOOR_STUCK:
			return "This door is already closed.";
		case DOOR_MISSING:
			return "There is no door there to close.";
		case DOOR_OPEN:
			cell.door_state = DOOR_CLOSED;
			UpdateDoorDisplay(c.r, c.c);
			return "You close the door.";
		default:
			return "";
	}
}

/*	MakeKinks - this function will look for long runs of horizontal
	hallways which emptiness above and below. If long enough, the run
	could be interrupted by a kink, either up or down or might have a
	deadend branch added to it. This is for someday.
*/
void Board::MakeKinks() {
}

// Apply display attributes appropriate for the given cell symbol.
// The cell_type disambiguates symbols that serve double duty ('+' is
// both spellbook on the floor and a closed door on a wall).
// Apply curses attributes appropriate for a rendered symbol and cell type.
void SetAttributes(WINDOW * win, bool on, int32_t c, CellBaseType cell_type) {
	int (*func)(WINDOW *, attr_t, void *) = on ? wattr_on : wattr_off;
	attr_t a = A_NORMAL;

	// A_BOLD is non-operative on line drawing characters.
	// A_DIM is non-operative on MacOS terminal.

	if (cell_type == DOOR) {
		// Doors are plain white — no special color.
		a = A_NORMAL;
	} else if (c == ACS_BULLET) {
		a = A_DIM;
	} else if (c == '+') {
		a = COLOR_PAIR(CLR_SPELLBOOKS);
	} else if (c == '#') {
		a = A_DIM;
	} else if (c == '<' || c == '>') {
		a = A_BOLD;
	}

	(*func)(win, a, nullptr);
}

// Return how many items are stacked on the given floor coordinate.
int32_t Board::GetGoodieCount(Coordinate & c) {
	int32_t retval = 0;
	auto it = goodies.find(c);
	if (it != goodies.end()) {
		retval = (int32_t)it->second.size();
	}
	return retval;
}

// Return the visible symbol for the top item at a coordinate, if any.
int32_t Board::GetSymbol(Coordinate c) {
	int32_t retval = -1;
	auto it = goodies.find(c);
	if (it != goodies.end()) {
		auto & v = it->second;
		if (!v.empty()) {
			retval = v.back()->symbol;
		}
	}
	return retval;
}

// Erase the message line and redraw the clock.
void Board::ClearInfoLine() {
	wmove(win, 0, 0);
	wclrtoeol(win);
	UpdateTime();
}

// Describe the quantity of items on the player's current tile.
void Board::ReportGoodies(Coordinate & c) {
	if (GetSymbol(c) > 0) {
		stringstream ss;
		int32_t goodie_count = GetGoodieCount(c);
		assert(goodie_count > 0);
		ss << (goodie_count > 1 ? "There are " : "There is ");
		ss << goodie_count << " ";
		ss << (goodie_count > 1 ? "items here." : "item here.");
		wmove(win, 0, 0);
		waddstr(win, ss.str().c_str());
		if (my_log.is_open() && false)
			my_log << "Attempted to call out goodies at " << c.to_string() << endl;
	}
}

// Render a single board coordinate with the correct visible symbol.
void Board::Show(bool show_original, Coordinate & coord, const Cell & cell) {
	if (show_original)
		mvwaddch(win, BOARD_TOP_OFFSET + coord.r, coord.c, cell.original_c);
	else {
		int32_t symbol = GetSymbol(coord);
		// If there's an item on the floor, use its symbol. Otherwise
		// use the cell's display character. Pass the cell type so
		// SetAttributes can distinguish doors from floor items.
		CellBaseType render_type = cell.base_type;
		if (symbol >= 0) {
			render_type = ROOM;		// Item on floor — treat as room.
		} else {
			symbol = cell.display_c;
		}

		SetAttributes(win, true, symbol, render_type);
		mvwaddch(win, BOARD_TOP_OFFSET + coord.r, coord.c, symbol);
		SetAttributes(win, false, symbol, render_type);
	}
}

// Render the visible slice of the board plus status lines.
void Board::Display(Player & p, bool show_original, double tr) {
	extern uint32_t current_board;

	werase(win);

	for (int32_t r = 0; r < BOARD_ROWS; r++) {
		for (int32_t c = 0; c < BOARD_COLUMNS; c++) {
			Coordinate coord(r, c);
			Cell & cell = cells[r][c];

			// Don't show "nothing"
			if (cell.base_type == EMPTY)
				continue;

			if (show_original) {
				Show(show_original, coord, cell);
				continue;
			}

			/* 	Attempt at limiting visibility of walls you ought not
				be able to see. This is a nice idea but comes with its
				own set of problems so is left out.
			*/
			if (IsCorridor(p.pos) and cell.base_type == WALL and
				!cell.is_known /*and !IsNeighbor(p.pos, coord)*/
			) {
				continue;
			}

			// Always show walls, corridors, doors and stairs if known.
			if (
				(cell.base_type == WALL or
				 cell.base_type == CORRIDOR or
				 cell.base_type == DOOR or
				 IsAStairway(coord)
				) and
				cell.is_known
			) {
				Show(show_original, coord, cell);
				continue;
			}

			// If a floor is known and is covered by something, show
			// the something.
			if (
				cell.base_type == ROOM and
				cell.is_known and
				GetSymbol(coord) >= 0
			) {
				Show(show_original, coord, cell);
				continue;
			}

			// Don't show remaining cells that are beyond our torch.
			if (!(coord.Distance(p.pos) < tr)) {
				continue;
			}

			if (!LineOfSight(p.pos, coord))
				continue;

			// The cell is close by - it might be a wall, etc.
			// Mark it known.
			cell.is_known = true;

			Show(show_original, coord, cell);
		}
	}

	if (my_log.is_open())
		my_log << endl;

	UpdateTime();
	wmove(win, BOARD_STATUS_OFFSET, 0);
	wattron(win, COLOR_PAIR(CLR_EMPTY));
	waddstr(win, p.to_string_2().c_str());
	wattroff(win, COLOR_PAIR(CLR_EMPTY));

	wmove(win, BOARD_STATUS_OFFSET + 1, 0);
	wattron(win, COLOR_PAIR(CLR_EMPTY));
	waddstr(win, p.to_string_1().c_str());
	wattroff(win, COLOR_PAIR(CLR_EMPTY));
	// Caller is responsible for wrefresh.
}

// Trace a coarse ray between two cells to determine visibility.
bool Board::LineOfSight(Coordinate &p, Coordinate & other) {
	double distance = p.Distance(other);
	double delta = 1.0 / (distance + 1.0);
	if (distance <= 1)
		return true;

	if (my_log.is_open() and false) {
		my_log << "LOS p: " << p.to_string();
		my_log << " other: " << other.to_string();
		my_log << " dist: " << distance;
		my_log << " delta: " << delta;
	}
	for (double t = 0; t < 1.0; t += delta) {
		Coordinate s = p.LERP(other, t);
		if (my_log.is_open()) {
			my_log << " lerp: " << s.to_string();
		}
		Cell & los_cell = cells[s.r][s.c];
		// Closed doors block line of sight just like walls.
		bool door_blocks = (los_cell.base_type == DOOR &&
			los_cell.door_state != DOOR_OPEN &&
			los_cell.door_state != DOOR_MISSING);
		if (
			los_cell.base_type == EMPTY or
			los_cell.base_type == WALL or
			door_blocks
		) {
			if (my_log.is_open()) {
				my_log << " returning false\n";
			}
			return false;
		}
	}
	if (my_log.is_open()) {
		my_log << " returning true\n";
	}
	return true;
}

// Place the up and down staircases in distinct rooms.
void Board::PlaceStairs() {
	assert(rooms.size() > 1);
	ivec room_numbers;

	for (auto & r : rooms) {
		room_numbers.push_back(r.room_number);
	}
	shuffle(room_numbers.begin(), room_numbers.end(), default_random_engine(rand()));
	upstairs = GetGoodStairLocation(rooms[room_numbers[0]]);
	cells[upstairs.r][upstairs.c].display_c =
		cells[upstairs.r][upstairs.c].original_c = UP_STAIRS;
	downstairs = GetGoodStairLocation(rooms[room_numbers[1]]);
	cells[downstairs.r][downstairs.c].display_c =
		cells[downstairs.r][downstairs.c].original_c = DOWN_STAIRS;
	assert(upstairs != downstairs);
}

// Report whether a coordinate contains either staircase glyph.
bool Board::IsAStairway(Coordinate & c) {
	if ((c.r < 0 or c.r >= BOARD_ROWS) or
	    (c.c < 0 or c.c >= BOARD_COLUMNS))
		return false;
	assert(c.c >= 0 and c.c < BOARD_COLUMNS);
	return (cells[c.r][c.c].original_c == UP_STAIRS) or
			(cells[c.r][c.c].original_c == DOWN_STAIRS);
}

/*	Returns coordinates in Board space! The chosen coordinate is checked
	to make sure it is not already a stairway. By beginning with the
	room's centroid, we are guaranteed there is another room cell in
	the 3x3 neighborhood.
*/
Coordinate Board::GetGoodStairLocation(Room & room) {
	Coordinate retval = room.GetCentroid();
	while (true) {
		retval.c += RR(-1, 1);
		retval.r += RR(-1, 1);
		if (!IsAStairway(retval)) {
			// this will be very rare and does NOT constitute a
			// potential for an infinite loop.
			break;
		}
	}
	return retval;
}

// Report whether the coordinate is the level's downward staircase.
bool Board::IsDownstairs(Coordinate & c) {
	return IsAStairway(c) and
			cells[c.r][c.c].original_c == DOWN_STAIRS;
}

// Report whether the coordinate is the level's upward staircase.
bool Board::IsUpstairs(Coordinate & c) {
	return IsAStairway(c) and
			cells[c.r][c.c].original_c == UP_STAIRS;
}

/*	PlanBForCooridors() - this function attempts to find
	an acceptable corridor in cases where the global
	algorithm fails for a room. This method rebuilds
	the bad column and bad row vectors including only the
	afflicted room and its nearest neighbor.

	NOTE: Nearest neighbor depends upon the rooms already
	being "flattened."
*/

// Recover corridor connectivity for rooms missed by the main planner.
bool Board::PlanBForCooridors(uint32_t room_index) {
	Coordinate src = rooms.at(room_index).GetCentroid();
	double smallest_distance = DBL_MAX;
	uint32_t closest_neighbor = 0;

	for (uint32_t i = 0; i < rooms.size(); i++) {
		if (i == room_index)
			continue;
		Coordinate dst = rooms.at(i).GetCentroid();
		double d = sqrt((src.c - dst.c) * (src.c - dst.c) +
						(src.r - dst.r) * (src.r - dst.r));
		if (d < smallest_distance) {
			smallest_distance = d;
			closest_neighbor = i;
		}
	}
	if (false and my_log.is_open()) {
		my_log << "Closest neighbor to room: " << room_index;
		my_log << " is room: " << closest_neighbor << endl;
	}
	Coordinate dst = rooms.at(closest_neighbor).GetCentroid();
	LayCorridor(src, dst);
	return true;
}

// Flood-fill overlapping room regions so they share one final room id.
void Board::FlattenRooms() {
	vector<Coordinate> work_list;

	for (uint32_t room_index = 0; room_index < rooms.size(); room_index++) {
		work_list.clear();

		Coordinate c = rooms[room_index].GetCentroid();
		// If the centroid has already been flattened, the whole room
		// has been flattened.
		if (cells[c.r][c.c].has_been_flattened)
			continue;
		// The region containing this cell will be flattened to the
		// value of this cell.
		int32_t flattened_room_value = rooms[room_index].room_number;

		cells[c.r][c.c].has_been_added_to_work_list = true;
		work_list.push_back(c);

		// Here is the flood fill - remove an item from the work_list, process it
		// and add all its unprocessed room neighbors to the work_list.
		while (!work_list.empty()) {
			assert(work_list.size() < 1920);

			Coordinate c = work_list.back();
			Cell & cell = cells[c.r][c.c];
			work_list.pop_back();

			assert(cell.has_been_added_to_work_list);
			assert(cell.base_type == ROOM);

			cell.has_been_flattened = true;
			cell.final_room_number = flattened_room_value;
			cell.display_c = ACS_BULLET;

			for (int32_t dr = -1; dr <= 1; dr++) {
				for (int32_t dc = -1; dc <= 1; dc++) {
					if (dc == 0 and dr == 0)
						continue;

					Coordinate e_c = Coordinate(dr + c.r, dc + c.c);
					assert(e_c.r >= 0 and e_c.r < BOARD_ROWS);
					assert(e_c.c >= 0 and e_c.c < BOARD_COLUMNS);

					Cell & cell = cells[e_c.r][e_c.c];

					if (cell.has_been_added_to_work_list)
						continue;

					if (cell.base_type != ROOM)
						continue;

					if (cell.has_been_flattened)
						continue;

					cell.has_been_added_to_work_list = true;
					work_list.push_back(e_c);
				}
			}
		}
	}
}

// Dump a textual representation of selected board metadata to the log.
void Board::DebugPrintBoard(int32_t mode) {
	if (!my_log.is_open())
		return;

	if (mode == 0)
		my_log << "base_type\n";
	else if (mode == 1)
		my_log << "is_lit is deprecated\n";
	else if (mode == 2)
		my_log << "is_known\n";

	for (int32_t r = 0; r < BOARD_ROWS; r++) {
		for (int32_t c = 0; c < BOARD_COLUMNS; c++) {
			Cell & cell = cells[r][c];
			switch (mode) {
				case 0:
					my_log << cell.base_type;
					break;

				case 2:
					my_log << cell.is_known;
					break;

				default:
					break;
			}
		}
		my_log << endl;
	}
	my_log << endl;
}
