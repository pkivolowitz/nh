#include "room.hpp"
#include "utilities.hpp"

extern const int32_t BOARD_COLUMNS;
extern const int32_t BOARD_ROWS;
extern const int32_t BOARD_TOP_OFFSET;

/*	Rooms begin life as structured objects (based on top / left and
	bottom / right). The Board class turns these into the onscreen
	representation.

	By starting with the width and height, we can be assured of always
	generating rooms which fit on the board. This is superior to how
	I've done this before.
*/
void Room::Initialize(int32_t rn) {
	const int32_t MIN_WIDTH = 3;
	const int32_t MAX_WIDTH = 9;
	const int32_t MIN_HEIGHT = 4;
	const int32_t MAX_HEIGHT = 8;

	room_number = rn;
	int32_t w = RR(MIN_WIDTH, MAX_WIDTH);
	int32_t h = RR(MIN_HEIGHT, MAX_HEIGHT);
	tl.c = RR(1, BOARD_COLUMNS - w - 1);
	tl.r = RR(1, BOARD_ROWS - h - 1);
	br.c = tl.c + w;
	br.r = tl.r + h;
	centroid.c = (tl.c + br.c) / 2;
	centroid.r = (tl.r + br.r) / 2;

	is_lit = RR(0, 100) > 50;
	has_been_mapped = false;
}


Coordinate Room::GetCentroid() {
	return centroid;
}