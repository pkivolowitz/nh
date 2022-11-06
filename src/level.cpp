#include <iostream>
#include <fstream>
#include <vector>
#include <map>
#include <set>
#include <unordered_set>
#include <cassert>
#include <cstdlib>
#include <cmath>
#include <signal.h>

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

void Level::MakeRooms(Presentation * p) {
	//ENTERING();
	Coordinate tl, br;
	for (int room_number = MAX_ROOMS; room_number >= 0; room_number--) {
		vector<Coordinate> v;
		CalcRoomBoundaries(tl, br, p);
		FillRoomBoundaries(tl, br, v, room_number);
		if (room_number == MAX_ROOMS)
			continue;
		FlattenRoom(v, room_number);
	}
	//LEAVING();
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
	MakeRooms(p);
	AddBorders();
	AddHallways();
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
	for (auto & p : cells)
		p->Unflatten();
	while (index < v.size()) {
		CheckFloor(index, v, room_number);
		index++;
	}
	//LOGMESSAGE("index: " << index);
}

/*	CheckFloor - Like a convolution kernel, this function checks a cell's 8 neighbors
	to see if they are a) Floors and b) from a room with a higher index than the
	current room. Rooms are defined in decreasing order so that this makes sense. The
	algorithm isn't optimal, but with small arrays (24x80) this is irrelevant.
*/
void Level::CheckFloor(int index, vector<Coordinate> & v, int room_number) {
	//ENTERING();
	Coordinate center = v.at(index);
	int loop_counter = 0;
	for (int l = center.l - 1; l <= center.l + 1; l++) {
		if (l < 0 || l >= lines)
			continue;
		for (int c = center.c - 1; c <= center.c + 1; c++) {
			loop_counter++;
			if (loop_counter > 9)
				raise(SIGINT);

			if (c < 0 || c >= cols)
				continue;
			if (c == center.c && l == center.l)
				continue;
			Floor * cp = (Floor *) cells.at(Offset(l, c));
			if (cp->IsFlattened()) {
				continue;
			}
			if (cp->BT() == BaseType::FLOOR && cp->GetRoomNumber() > room_number) {
				cp->Flatten();
				cp->SetRoomNumber(room_number);
				v.push_back(Coordinate(l, c));
			}
		}
	}
	//LOGMESSAGE("returning loop counter was: " << loop_counter);
}

/*	FillRoomBoundaries - fills each cell with a Floor within the rectangle specified by tl and br.
	Each cell coordinate is added to a vector which is used to flood fill the room number in the
	step of level creation. Note that rooms are created with descending IDs.
*/
void Level::FillRoomBoundaries(Coordinate & tl, Coordinate & br, vector<Coordinate> & v, int room_number) {
	//ENTERING();
	for (int l = tl.l; l <= br.l; l++) {
		for (int c = tl.c; c <= br.c; c++) {
			assert(l < lines && c < cols);
			v.push_back(Coordinate(l, c));
			Replace(l, c, new Floor(room_number));
		}
	}
	//LEAVING();
}

void Level::CalcRoomBoundaries(Coordinate & tl, Coordinate & br, Presentation * p) {
	assert(p != nullptr);
	tl = Coordinate(rand() % (lines - p->COMMAND_LINES - p->STATUS_LINES - 1) + 1, rand() % (cols - 2 - MIN_ROOM_WIDTH) + 1);
	Coordinate dims(rand() % MAX_ROOM_HEIGHT_RAND + MIN_ROOM_HEIGHT, rand() % MAX_ROOM_WIDTH_RAND + MIN_ROOM_WIDTH);
	br = tl + dims;
	br.Clip(lines, cols);
}

void Level::Replace(int l, int c, CellPtr cell) {
	//ENTERING();
	int o = Offset(l, c);
	if (cells.at(o) != nullptr) {
		delete cells.at(o);
	}
	cells.at(o) = cell;
	//LEAVING();
}

int Level::Offset(int l, int c) {
	int o = l * cols + c;
	assert(o >= 0);
	assert(o < lines * cols);
	return o;
}

int Level::Offset(Coordinate c) {
	return Offset(c.l, c.c);
}

Level::RCMap Level::CharacterizeRooms() {
	RCMap rcmap;
	for (int l = 0; l < lines; l++) {
		for (int c = 0; c < cols; c++) {
			Coordinate cell_coord(l, c);
			int o = Offset(cell_coord);
			FloorPtr p = (FloorPtr) cells.at(o);
			if (p->BT() != BaseType::FLOOR)
				continue;
			auto it = rcmap.find(p->GetRoomNumber());
			if (it == rcmap.end()) {
				RoomCharacterization rc;
				rc.top_left = cell_coord;
				rc.bot_right = cell_coord;
				rcmap.insert(std::pair<int, RoomCharacterization>(p->GetRoomNumber(), rc));
			} else {
				RoomCharacterization * rcptr = &(it->second);
				if (cell_coord.l < rcptr->top_left.l)
					rcptr->top_left.l = cell_coord.l;
				if (cell_coord.l > rcptr->bot_right.l)
					rcptr->bot_right.l = cell_coord.l;
				if (cell_coord.c < rcptr->top_left.c)
					rcptr->top_left.c = cell_coord.c;
				if (cell_coord.c > rcptr->bot_right.c)
					rcptr->bot_right.c = cell_coord.c;
			}
		}
	}
	for (auto & rc : rcmap) {
		rc.second.centroid = Coordinate::Centroid(rc.second.top_left, rc.second.bot_right);
		LOGMESSAGE("Room: " << rc.first << " Centroid: (" << rc.second.centroid.l << ", " << rc.second.centroid.c << ")");
	}
	return rcmap;
}

void Level::NSEW(int s, int e, int fixed_value, RCMap & rcm, bool is_ew) {
	//ENTERING();
	if (s > e) {
		int t = s;
		s = e;
		e = t;
	}
	assert(s <= e);
	int loop_counter = 0;

	for (int c = s; c <= e; c++) {
		//LOGMESSAGE("Top Of Loop");
		if (++loop_counter > 1000) {
			LOGMESSAGE("INFINITE LOOP SHORT CIRCUITED");
			raise(SIGINT);
		}
		CellPtr cp = ((is_ew) ? cells.at(Offset(fixed_value, c)) : cells.at(Offset(c, fixed_value)));
		if (cp->BT() == BaseType::FLOOR) {
			FloorPtr fp = (FloorPtr) cp;
			rcm[fp->GetRoomNumber()].connected =true;
			continue;
		}	
		if (cp->BT() == BaseType::HALLWAY)
			continue;	
		if (cp->BT() == BaseType::ROCK && (is_ew ? Border::IsBadForEastWest(cp->Symbol()) : Border::IsBadForNorthSouth(cp->Symbol()))) {
			//continue;
			if (is_ew) {
				if (fixed_value >= lines - 1)
					continue;
				else
					fixed_value++;
			} else {
				if (fixed_value >= cols - 1)
					continue;
				else
					fixed_value++;
			}
			c--;
			cp = ((is_ew) ? cells.at(Offset(fixed_value, c)) : cells.at(Offset(c, fixed_value)));
		}
		//LOGMESSAGE("Before Door");
		//bool make_door;
		if (is_ew) {
			//make_door = Border::IsNorthSouth(cp->Symbol());
			Replace(fixed_value, c, cp = new Hallway());
		} else {
			//make_door = Border::IsEastWest(cp->Symbol());
			Replace(c, fixed_value, cp = new Hallway());			
		}
		/*
		if (make_door)
			cp->SetDoor((rand() % 2) ? DOOR_OPEN : DOOR_CLOSED);
		*/
	}
	//LEAVING();	
}

void Level::Manhattan(Coordinate & c1, Coordinate & c2, RCMap & rcm) {
	//ENTERING();
	if (rand() % 2) {
		NSEW(c1.c, c2.c, c1.l, rcm, true);
		NSEW(c1.l, c2.l, c2.c, rcm, false);
	} else {
		NSEW(c1.c, c2.c, c2.l, rcm, true);
		NSEW(c1.l, c2.l, c1.c, rcm, false);
	}
	//LEAVING();
}

/*	good_lines and good_cols are ones which have no values in common with the
	edges of rooms. In this way, I am guaranteed of avoiding a hallway that 
	runs down the edge of a wall (undesirable).
*/

void Level::AddHallways() {
	RCMap rcm = CharacterizeRooms();
	LOGMESSAGE("rcmap size: " << rcm.size());
	vector<int> good_lines;
	vector<int> good_cols;
	map<int, vector<Coordinate>> squares_by_room;
	BuildSquareMap(squares_by_room);
	FindGoodLinesAndColumns(rcm, good_lines, good_cols);
	vector<Coordinate> corners;
	MakeCorners(corners, good_lines, good_cols);
	for (unsigned int c = 0; c < corners.size() - 1; c++) {
		Manhattan(corners.at(c), corners.at(c+1), rcm);
	}
	while (true) {
		int room_number = FindFirstDisconnectedRoom(rcm);
		LOGMESSAGE("Disconnected room: " << room_number);
		if (room_number < 0)
			break;
		// NOTE NOTE NOTE - This may select a cell on a bad row or column.
		Coordinate starting_point = squares_by_room[room_number].at(rand() % squares_by_room[room_number].size());
		Coordinate closest_hallway = FindClosestHallway(starting_point);
		Manhattan(starting_point, closest_hallway, rcm);
		LogConnectivity(rcm);
	}
	AddJinks();
	//AddDoors();
	LEAVING();
}

void Level::BuildSquareMap(std::map<int, std::vector<Coordinate>> & squares_by_room) {
	for (int l = 0; l < lines; l++) {
		for (int c = 0; c < cols; c++) {
			Coordinate b(l, c);
			FloorPtr p = (FloorPtr) cells.at(Offset(l, c));
			if (p->BT() == BaseType::FLOOR) {
				squares_by_room[p->GetRoomNumber()].push_back(b);
			}
		}
	}	
}

static float Distance(Coordinate & a, Coordinate & b) {
	float x = float(a.c - b.c);
	float y = float(a.l - b.l);
	return sqrtf(x * x + y * y);
}

Coordinate Level::FindClosestHallway(Coordinate & a) {
	/*	This is brute force - the saving grace is the small board size. */
	Coordinate retval;
	float distance = 9999999.0;
	for (int l = 0; l < lines; l++) {
		for (int c = 0; c < cols; c++) {
			Coordinate b(l, c);
			if (cells.at(Offset(l, c))->BT() == BaseType::HALLWAY) {
				if (Distance(a, b) < distance) {
					retval = b;
					distance = Distance(a, b);
				}
			}
		}
	}
	return retval;
}

int Level::FindFirstDisconnectedRoom(RCMap & rcm) {
	int retval = -1;
	for (auto & rc : rcm) {
		if (!rc.second.connected) {
			retval = rc.first;
			break;
		}
	}
	return retval;
}
/*	LogConnectivity() - will log the connectivity status of each room in an RCMap.
*/

void Level::LogConnectivity(RCMap & rcm) {
	if (_Log.is_open()) {
		_Log << "Connectivity Report: " << rcm.size() << " rooms." << endl;
		for (auto & rm : rcm) {
			_Log << "Room: " << rm.first << " " << (rm.second.connected ? "Connected" : "Unconnected") << endl;
		}
	}
}

/*	FindGoodLinesAndColumns() - I don't want hallways to pass along / through the exterior walls
	of rooms. This function eliminates tops, lefts, rights and bottoms. For compound rooms, 
	other walls can still be hit. This is handled elsewhere.
*/

void Level::FindGoodLinesAndColumns(RCMap & rcm, std::vector<int> & good_lines, std::vector<int> & good_cols) {
	set<int> templ;
	set<int> tempc;
	// First create sets with all possible rows and columns.
	for (int i = 1; i < lines - 1; i++)
		templ.insert(i);
	for (int i = 1; i < cols - 1; i++)
		tempc.insert(i);
	for (int l = 0; l < lines; l++) {
		for (int c = 0; c < cols; c++) {
			RockPtr p = (RockPtr) cells.at(Offset(l, c));
			if (p->BT() == BaseType::ROCK && Border::IsCorner(p->Symbol())) {
				templ.erase(l);
				tempc.erase(c);
			}
		}
	}
	// Convert the sets of what remains into vectors permitting easy random choices of just the right values.
	std::copy(templ.begin(), templ.end(), std::back_inserter(good_lines));
	std::copy(tempc.begin(), tempc.end(), std::back_inserter(good_cols));
}

void Level::MakeCorners(vector<Coordinate> & corners, vector<int> & good_lines, vector<int> & good_cols) {
	bool filling_in = corners.size() > 0;
	int number_of_corners = (rand() % 8) + (filling_in ? 1 : 4);
	for (int c = 0; c < number_of_corners; c++) {
		Coordinate coord;
		coord.l = good_lines.at(rand() % (good_lines.size() - 2) + 1);
		coord.c = good_cols.at(rand() % (good_cols.size() - 2) + 1);
		if (filling_in)
			corners.insert(corners.end() - 1, coord);
		else
			corners.push_back(coord);
	}
}

void Level::AddJinks() {
	for (int l = 1; l < lines - 2; l++) {
		//int starting_l = l;
		int run_length = 0;
		for (int c = 1; c < cols - 2; c++) {
			if (cells.at(Offset(l, c))->BT() == BaseType::HALLWAY &&
				cells.at(Offset(l - 1, c))->BT() == BaseType::ROCK &&
				cells.at(Offset(l + 1, c))->BT() == BaseType::ROCK) {
					//if (run_length == 0)
					//	starting_l = l;
					run_length++;
			} else {
				// Either a run just ended or one never started.
				if (run_length < 3) {
					run_length = 0;
					continue;
				}
				// Run is three or more hallway spots so attempt to put a jink here.
			}
		}
	}
}

void Level::AddDoors() {
	for (int l = 1; l < lines - 1; l++)
		for (int c = 1; c < cols - 1; c++) {
			if ((cells.at(Offset(l, c))->BT() == BaseType::HALLWAY &&
				cells.at(Offset(l + 1, c))->BT() == BaseType::HALLWAY &&
				cells.at(Offset(l + 1, c + 1))->BT() == BaseType::HALLWAY &&
				cells.at(Offset(l, c + 1))->BT() == BaseType::HALLWAY) ||
				(cells.at(Offset(l, c))->BT() == BaseType::HALLWAY &&
				cells.at(Offset(l - 1, c))->BT() == BaseType::HALLWAY &&
				cells.at(Offset(l - 1, c - 1))->BT() == BaseType::HALLWAY &&
				cells.at(Offset(l, c - 1))->BT() == BaseType::HALLWAY)) 
			{
				if (rand() % 5 == 0)
					Replace(l, c, new Rock());
			}
			
		}
}

void Level::Render(Presentation * p) {
	CalculateVisibility();
	for (int l = 0; l < lines; l++) {
		p->Move(l + p->TOP_DRAWABLE_LINE, p->LEFT_DRAWABLE_COL);
		for (int c = 0; c < cols; c++) {
			CellPtr cp = cells.at(Offset(l, c));
			chtype s = (cp->IsVisible()) ? cp->Symbol() : ' ';
			if (cp->BT() == BaseType::FLOOR)
				s = (chtype) (((Floor *) cp)->GetRoomNumber() + '0');
			p->AddCh(s);
		}
	}
}

/*	This is a stub.
*/
void Level::CalculateVisibility() {
	for (int l = 0; l < lines; l++) {
		for (int c = 0; c < cols; c++) {
			cells.at(Offset(l, c))->SetVisibility(true);
		}
	}
}

void Level::AddBorders() {
	ENTERING();
	Border b;
	for (int row = 0; row < lines; row++) {
		for (int column = 0; column < cols; column++) {
			Coordinate coord(row, column);
			if (cells.at(Offset(coord))->BT() != BaseType::ROCK)
				continue;
			BorderFlags bf = EvaluateBorder(coord);
			if (bf != 0) {
				//LOGMESSAGE("bf: " << hex << (unsigned int) bf << dec << " alt_charmap size: " << b.alt_charmap.size());
				if (b.alt_charmap.find(bf) != b.alt_charmap.end())
					((RockPtr) cells.at(Offset(coord)))->SetSymbol(b.alt_charmap[bf]);
			}
		}
	}
	LEAVING();
}

/*	EvaluateBorder() - this function is called for every ROCK cell. It examines
	it's eight neighbors looking for rooms. If any are found, the symbol rendered
	for this rock is changed to the appropriate border. This function characterizes
	the neighborhood.
*/
BorderFlags Level::EvaluateBorder(Coordinate & center) {
	BorderFlags bf = 0;
	Coordinate other;
	// Check line above.
	if (center.l > 0) {
		other.l = center.l - 1;
		// Check left
		if (center.c > 0) {
			other.c = center.c - 1;
			bf |= (cells.at(Offset(other))->BT() == BaseType::FLOOR) ? RLEFT_UP : 0;
		}
		// Check right
		if (center.c < cols - 2) {
			other.c = center.c + 1;
			bf |= (cells.at(Offset(other))->BT() == BaseType::FLOOR) ? RRIGHT_UP : 0;
		}
		// Check center
		other.c = center.c;
		bf |= (cells.at(Offset(other))->BT() == BaseType::FLOOR) ? RUP : 0;
	}
	// Check current line.
	other.l = center.l;
	// Check left
	if (center.c > 0) {
		other.c = center.c - 1;
		bf |= (cells.at(Offset(other))->BT() == BaseType::FLOOR) ? RLEFT : 0;
	}
	// Check right
	if (center.c < cols - 2) {
		other.c = center.c + 1;
		bf |= (cells.at(Offset(other))->BT() == BaseType::FLOOR) ? RRIGHT : 0;
	}
	//LOGMESSAGE("coordinate: (" << center.l << ", " << center.c << ") (" << lines << ", " << cols << ")");
	// Check line below.
	if (center.l < lines - 2) {
		other.l = center.l + 1;
		// Check left
		if (center.c > 0) {
			other.c = center.c - 1;
			bf |= (cells.at(Offset(other))->BT() == BaseType::FLOOR) ? RLEFT_DOWN : 0;
		}
		// Check right
		if (center.c < cols - 2) {
			other.c = center.c + 1;
			bf |= (cells.at(Offset(other))->BT() == BaseType::FLOOR) ? RRIGHT_DOWN : 0;
		}
		// Check center
		other.c = center.c;
		bf |= (cells.at(Offset(other))->BT() == BaseType::FLOOR) ? RDOWN : 0;
	}
	return bf;
}
// - Cell ------------------------------------------------------------------- //

const chtype Cell::base_type_symbols[3] = {' ', '#', '.'};

Cell::Cell() {
	//ENTERING();
	flags.passable = false;
	//flags.door = DOOR_NOT;
	flags.blocks_line_of_sight = true;
	flags.flattened = 0;
}

Cell::~Cell() {
	//ENTERING();
}

chtype Cell::Symbol() {
	chtype retval = fl.Top();
	if (retval == '\0') {
		retval = base_type_symbols[(int) bt];
		/*
		if (flags.door == DOOR_CLOSED)
			retval = '+';
		else if (flags.door == DOOR_OPEN)
			retval = '-';
		*/
	}
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

void Cell::SetSymbol(chtype c) {
	symbol = c;
}

// - Rock ------------------------------------------------------------------- //

Rock::Rock() {
	//ENTERING();
	bt = BaseType::ROCK;
	symbol = ' ';
}

chtype Rock::Symbol() {
	return symbol;
}

Rock::~Rock() {
	//ENTERING();
}

// - Hallway ---------------------------------------------------------------- //

Hallway::Hallway() {
	//ENTERING();
	bt = BaseType::HALLWAY;
}

Hallway::~Hallway() {
	//ENTERING();
}

// - Floor ------------------------------------------------------------------ //

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

