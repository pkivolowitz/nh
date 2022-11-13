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
	// shuffle(key_points.begin(), key_points.end(), std::default_random_engine(rand()));
	for (uint32_t index = 0; index < key_points.size() - 1; index++) {
		Coordinate &src = key_points[index];
		Coordinate &dst = key_points[index + 1];
		LayCorridor(src, dst);
	}

	for (auto r : needs_plan_b) {
		PlanBForCooridors(r);
	}
}

void MakeCorridore(Cell & c) {
	if (isdigit(c.original_c))
		return;
	c.display_c = c.original_c = '#';
	c.base_type = CORRIDOR;
	c.final_room_number = -1;
}

void Board::LayCorridor(Coordinate & src, Coordinate & dst) {
	if (src.c != dst.c) {
		int32_t dc = (src.c < dst.c) ? 1 : -1;
		int32_t r = src.r;
		for (int32_t c = src.c; c != dst.c; c += dc) {
			if (c < 0 or c >= BOARD_COLUMNS)
				break;
			MakeCorridore(cells[r][c]);
		}
	}
	if (src.r != dst.r) {
		int32_t dr = (src.r < dst.r) ? 1 : -1;
		int32_t c = dst.c;
		for (int32_t r = src.r; r != dst.r; r += dr) {
			if (r < 0 or r >= BOARD_ROWS)
				break;
			MakeCorridore(cells[r][c]);
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
			cells[r][c].is_lit = rm.is_lit;
		}
	}
}

inline void SetCell(Cell & cell, CellBaseType bt, int32_t c, bool il) {
	cell.base_type = bt;
	cell.original_c = c;
	cell.is_lit = il;
}

void Board::Enclose(int32_t rn) {
	Room & rm = rooms[rn];
	for (int32_t r = rm.tl.r; r < rm.br.r; r++) {
		assert(r < BOARD_ROWS);
		assert(rm.tl.c > 0);
		assert(rm.br.c < BOARD_COLUMNS);
		if (!cells[r][rm.tl.c - 1].original_c) {
			SetCell(cells[r][rm.tl.c - 1], WALL, ACS_VLINE, rm.is_lit);
		}
		if (!cells[r][rm.br.c].original_c) {
			SetCell(cells[r][rm.br.c], WALL, ACS_VLINE, rm.is_lit);
		}
	}
	for (int32_t c = rm.tl.c - 1; c < rm.br.c + 1; c++) {
		assert(c < BOARD_COLUMNS);
		assert(rm.tl.r > 0);
		assert(rm.br.r < BOARD_ROWS);
		if (!cells[rm.tl.r - 1][c].original_c) {
			SetCell(cells[rm.tl.r - 1][c], WALL, ACS_HLINE, rm.is_lit);
		}
		if (!cells[rm.br.r][c].original_c) {
			SetCell(cells[rm.br.r][c], WALL, ACS_HLINE, rm.is_lit);
		}
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
	//RemoveFloorDigits();
	FlattenRooms();
	PlaceStairs();
	//DebugPrintBoard(0);
	DebugPrintBoard(1);
	DebugPrintBoard(2);
}

/* void Board::RemoveFloorDigits() {
	for (int32_t r = 0; r < BOARD_ROWS; r++) {
		for (int32_t c = 0; c < BOARD_COLUMNS; c++) {
			if (isdigit(cells[r][c].original_c)) {
				//cells[r][c].display_c =
				//	(show_floor) ? cells[r][c].original_c : ACS_BULLET;
			}
		}
	}
}
 */
void Board::Show(bool show_original, int32_t r, int32_t c, const Cell & cell) {
	if (show_original)
		mvaddch(BOARD_TOP_OFFSET + r, c, cell.original_c);
	else
		mvaddch(BOARD_TOP_OFFSET + r, c, cell.display_c);
}

void Board::Display(Player & p, bool show_original) {
	erase();
	int32_t pfrn = cells[p.pos.r][p.pos.c].final_room_number;

	for (int32_t r = 0; r < BOARD_ROWS; r++) {
		for (int32_t c = 0; c < BOARD_COLUMNS; c++) {
			Coordinate coord(r, c);
			Cell & cell = cells[r][c];

			// Don't show "nothing"
			if (cell.base_type == EMPTY)
				continue;
			
			// If a cell is:
			//	- not a stairway and 
			//	- is a room and
			//	- it belongs to a room other than that the player is in
			// then don't show it.
			if (cell.base_type == ROOM and 
				cell.final_room_number != pfrn and
				!IsAStairway(coord))
			{
					continue;
			}

			// Always show walls, corridors and stairs if
			// they are known (seen before).
			if (
				(cell.base_type == WALL or 
				 cell.base_type == CORRIDOR or 
				 IsAStairway(coord)
				) and 
				cell.is_known
			) {
				Show(show_original, r, c, cell);
				continue;
			}

			// If the cell is close by, mark it as known.
			if (coord.Distance(p.pos) < 2.5) {
				cell.is_known = true;
			}

			// Show the cell if:
			//	- the cell is lit and in line of sight or
			// 	- the cell has been seen previously

			if ((cell.is_lit and LineOfSight(p.pos, coord)) or
				(cell.is_known)) {
				if (
					(cell.base_type == WALL or cell.base_type == CORRIDOR) and 
					!cell.is_known
				) {
					continue;
				}
				cell.is_known = true;
				Show(show_original, r, c, cell);
				continue;
			}
		}
	}
	move(0, 0);
	stringstream ss;
	ss << "Seed: " << setw(8) << left << seed;
	ss << "Screen: " << setw(6) << left << screen_counter;
	addstr(ss.str().c_str());
}

bool Board::LineOfSight(Coordinate &player, Coordinate cell) {
	return true;
}

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

bool Board::IsDownstairs(Coordinate & c) {
	return IsAStairway(c) and 
			cells[c.r][c.c].original_c == DOWN_STAIRS;
}

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
	if (false and my_log.is_open()) {
		my_log << "Closest neighbor to room: " << room_index;
		my_log << " is room: " << closest_neighbor << endl;
	}
	Coordinate dst = rooms.at(closest_neighbor).GetCentroid();
	LayCorridor(src, dst);
	return true;
}

void Board::FlattenRooms() {
	vector<Coordinate> work_list;

	for (uint32_t room_index = 0; room_index < rooms.size(); room_index++) {
		work_list.clear();
		bool is_lit;

		Coordinate c = rooms[room_index].GetCentroid();
		// If the centroid has already been flattened, the whole room 
		// has been flattened.
		if (cells[c.r][c.c].has_been_flattened)
			continue;
		is_lit = rooms[room_index].is_lit;
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
			cell.is_lit = is_lit;
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

					// if (my_log.is_open()) {
					// 	my_log << "work list size is: " << work_list.size();
					// 	my_log << " adding coordinate: " << e_c.to_string() << endl;
					// }
				}
			}
			// if (my_log.is_open())
			// 	my_log << "work list size is: " << work_list.size() << endl;
		}
	}
}

void Board::DebugPrintBoard(int32_t mode) {
	if (!my_log.is_open())
		return;

	if (mode == 0)
		my_log << "base_type\n";
	else if (mode == 1)
		my_log << "is_lit\n";
	else if (mode == 2)
		my_log << "is_known\n";

	for (int32_t r = 0; r < BOARD_ROWS; r++) {
		for (int32_t c = 0; c < BOARD_COLUMNS; c++) {
			Cell & cell = cells[r][c];
			switch (mode) {
				case 0:
					my_log << cell.base_type;
					break;

				case 1:
					my_log << cell.is_lit;
					break;

				case 2:
					my_log << cell.is_known;
					break;
			}
		}
		my_log << endl;
	}
	my_log << endl;
}
