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

using namespace std;

extern ofstream my_log;
extern bool show_floor;

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
			if (cells[r][c].c == ACS_HLINE) {
				r_avoid.push_back(r);
				break;
			}
		}
	}
	if (my_log.is_open()) {
		my_log << "Rows to avoid: ";
		for (auto i : r_avoid)
			my_log << i << " ";
		my_log << endl;
	}
}

/*	FindRowsToAvoid
	FindColsToAvoid

	Called prior to laying out corridors, this function builds an ivec
	which contains the columns and rows for which corridors should be
	avoided. The reason is to avoid having a corridor run along the
	edge of a room. While this would make some sense as being an open
	cavern, the appearence is ugly.
*/
void Board::FindColsToAvoid(ivec &c_avoid) {
	for (int32_t c = 0; c < BOARD_COLUMNS; c++) {
		for (int32_t r = 0; r < BOARD_ROWS; r++) {
			if (cells[r][c].c == ACS_VLINE) {
				c_avoid.push_back(c);
				break;
			}
		}
	}
	if (my_log.is_open()) {
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
	if (my_log.is_open()) {
		my_log << "Room: " << r.room_number << " ";
		my_log << coord.r << " " << coord.c << endl;
	}
}

void Board::PlaceCorridors() {
	ivec bc; // bad_columns
	ivec br; // bad_rows

	FindColsToAvoid(bc);
	FindRowsToAvoid(br);
	if (my_log.is_open()) {
		my_log << "ColsToAvoid.size() " << bc.size() << endl;
		my_log << "RowsToAvoid.size() " << br.size() << endl;
	}

	vector<Coordinate> key_points;
	for (auto &r : rooms) {
		Coordinate coord;
		FindGCoords(br, bc, r, coord);
		if (coord.c < 0 || coord.r < 0) {
			PlanBForCooridors(r.room_number);
			continue;
		}
		key_points.push_back(coord);
	}
	if (my_log.is_open()) {
		my_log << "KeyPoint.size() " << key_points.size() << endl;
	}

	assert(key_points.size() > 0);
	// shuffle(key_points.begin(), key_points.end(), std::default_random_engine(rand()));
	for (uint32_t index = 0; index < key_points.size() - 1; index++) {
		Coordinate &src = key_points[index];
		Coordinate &dst = key_points[index + 1];
		LayCorridor(src, dst);
	}
}

void Board::LayCorridor(Coordinate & src, Coordinate & dst) {
	if (src.c != dst.c) {
	int32_t dc = (src.c < dst.c) ? 1 : -1;
	int32_t r = src.r;
	for (int32_t c = src.c; c != dst.c; c += dc) {
		if (c < 0 or c >= BOARD_COLUMNS)
			break;
		if (isdigit(cells[r][c].c))
			continue;
		cells[r][c].display_c = cells[r][c].c = '#'; //'0' + index;
		cells[r][c].base_type = CORRIDOR;
	}
	}
	if (src.r != dst.r) {
		int32_t dr = (src.r < dst.r) ? 1 : -1;
		int32_t c = dst.c;
		for (int32_t r = src.r; r != dst.r; r += dr) {
			if (r < 0 or r >= BOARD_ROWS)
				break;
			if (isdigit(cells[r][c].c))
				continue;
			cells[r][c].display_c = cells[r][c].c = '#'; //'0' + index;
			cells[r][c].base_type = CORRIDOR;
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
			else if (!cells[R][C].c)
				retval.push_back(' ');
			else if (isdigit(cells[R][C].c))
				retval.push_back('F');
			else if (cells[R][C].c == ACS_HLINE)
				retval.push_back('H');
			else if (cells[R][C].c == ACS_VLINE)
				retval.push_back('V');
			else {
				retval.push_back(' ');
			}
		}
	}

	return retval;
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
				cells[r][c].display_c = cells[r][c].c;
			}
		}
	}
}

/*	Fill() - an intermediate step in incrementally building the
	renderable board.
*/
void Board::Fill(int32_t rn) {
	Room *rptr = &rooms[rn];
	for (int32_t r = rptr->tl.r; r < rptr->br.r; r++) {
		for (int32_t c = rptr->tl.c; c < rptr->br.c; c++) {
			assert(c > 0);
			assert(r < BOARD_ROWS);
			assert(c < BOARD_COLUMNS);
			cells[r][c].c = '0' + rn;
			cells[r][c].display_c = '0' + rn;
			cells[r][c].base_type = ROOM;
		}
	}
}

void Board::Enclose(int32_t rn) {
	Room *rptr = &rooms[rn];
	for (int32_t r = rptr->tl.r; r < rptr->br.r; r++) {
		assert(r < BOARD_ROWS);
		assert(rptr->tl.c > 0);
		assert(rptr->br.c < BOARD_COLUMNS);
		if (!cells[r][rptr->tl.c - 1].c)
			cells[r][rptr->tl.c - 1].c = ACS_VLINE;
		if (!cells[r][rptr->br.c].c)
			cells[r][rptr->br.c].c = ACS_VLINE;
	}
	for (int32_t c = rptr->tl.c - 1; c < rptr->br.c + 1; c++) {
		assert(c < BOARD_COLUMNS);
		assert(rptr->tl.r > 0);
		assert(rptr->br.r < BOARD_ROWS);
		if (!cells[rptr->tl.r - 1][c].c)
			cells[rptr->tl.r - 1][c].c = ACS_HLINE;
		if (!cells[rptr->br.r][c].c)
			cells[rptr->br.r][c].c = ACS_HLINE;
	}
}

void Board::Create() {
	extern bool no_corridors;
	const int32_t MIN_ROOMS = 5;
	const int32_t MAX_ROOMS = 9;
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
	}
	RemoveFloorDigits();
	FlattenRooms();
	PlaceStairs();
}

void Board::RemoveFloorDigits() {
	for (int32_t r = 0; r < BOARD_ROWS; r++) {
		for (int32_t c = 0; c < BOARD_COLUMNS; c++) {
			if (isdigit(cells[r][c].c)) {
				cells[r][c].display_c = cells[r][c].c =
					(show_floor) ? cells[r][c].c : ' ';
			}
		}
	}
}

void Board::Display(bool show_original) {
	erase();
	for (int32_t r = 0; r < BOARD_ROWS; r++) {
		move(BOARD_TOP_OFFSET + r, 0);
		for (int32_t c = 0; c < BOARD_COLUMNS; c++) {
			if (show_original)
				addch((cells[r][c].c) ? cells[r][c].c : ACS_BULLET);
			else
				addch((cells[r][c].display_c) ? cells[r][c].display_c : ACS_BULLET);
		}
	}
	move(0, 0);
	stringstream ss;
	ss << "Seed: " << setw(8) << left << seed;
	ss << "Screen: " << setw(6) << left << screen_counter;
	addstr(ss.str().c_str());
}

void Board::PlaceStairs() {
	assert(rooms.size() > 1);
	ivec room_numbers;

	for (auto & r : rooms) {
		room_numbers.push_back(r.room_number);
	}
	shuffle(room_numbers.begin(), room_numbers.end(), default_random_engine(rand()));
	upstairs = GetGoodStairLocation(rooms[room_numbers[0]]);
	cells[upstairs.r][upstairs.c].display_c = cells[upstairs.r][upstairs.c].c = '<';
	downstairs = GetGoodStairLocation(rooms[room_numbers[1]]);
	cells[downstairs.r][downstairs.c].display_c = cells[downstairs.r][downstairs.c].c = '>';
	assert(upstairs != downstairs);
}

/*	Returns coordinates in Board space!
*/
Coordinate Board::GetGoodStairLocation(Room & room) {
	Coordinate retval = room.GetCentroid();
	retval.c += RR(-1, 1);
	retval.r += RR(-1, 1);
	return retval;
}

/*	PlanBForCooridors() - this function attempts to find
	an acceptable corridor in cases where the global 
	algorithm fails for a room. This method rebuilds
	the bad column and bad row vectors including only the
	afflicted room and its nearest neighbor.

	NOTE: Nearest neighbor depends upon the rooms already
	being "flattened."
*/

bool Board::PlanBForCooridors(uint32_t room_index) {
	Coordinate src = rooms.at(room_index).GetCentroid();
	double smallest_distance = DBL_MAX;
	uint32_t closest_neighbor;

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
	if (my_log.is_open()) {
		my_log << "Closest neighbor to room: " << room_index;
		my_log << " is room: " << closest_neighbor << endl;
	}
	return true;
}

void Board::FlattenRooms() {
	vector<Coordinate> work_list;

	for (uint32_t room_index = 0; room_index < rooms.size(); room_index++) {
		work_list.clear();

		Coordinate c = rooms[room_index].GetCentroid();
		// If the centroid has already been flattened, the whole room has been flattened.
		if (cells[c.r][c.c].has_been_flattened)
			continue;
		// The region containing this cell will be flattened to the value of this cell.
		int32_t flattened_room_value = cells[c.r][c.c].c;
		cells[c.r][c.c].has_been_added_to_work_list = true;
		// Seed the work_list with the centroid's coordinate.
		work_list.push_back(c);

		// Here is the flood fill - remove an item from the work_list, process it
		// and add all its unprocessed room neighbors to the work_list.
		while (!work_list.empty()) {
			assert(work_list.size() < 1920);

			Coordinate c = work_list.back();
			work_list.pop_back();

			assert(cells[c.r][c.c].has_been_added_to_work_list);
			assert(cells[c.r][c.c].base_type == ROOM);
			cells[c.r][c.c].has_been_flattened = true;
			cells[c.r][c.c].c = flattened_room_value;
			cells[c.r][c.c].display_c = flattened_room_value;

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
					if (my_log.is_open()) {
						my_log << "work list size is: " << work_list.size();
						my_log << " adding coordinate: " << e_c.to_string() << endl;
					}
				}
			}
			if (my_log.is_open())
				my_log << "work list size is: " << work_list.size() << endl;
		}
	}
}

