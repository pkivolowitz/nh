#include <iostream>
#include <string.h>
#include <ncurses.h>
#include <getopt.h>
#include <vector>
#include <cassert>
#include <fstream>
#include <sstream>
#include <algorithm>
#include <random>
#include <ctime>
#include "game_time.hpp"
#include "drawing_support.hpp"
#include "cell.hpp"
#include "coordinate.hpp"
#include "utilities.hpp"
#include "room.hpp"
#include "board.hpp"
#include "player.hpp"

using namespace std;

int32_t seed = 0;
int32_t screen_counter = 0;
//bool show_floor = false;
bool no_corridors = false;
bool show_original = false;

ofstream my_log;

void InitCurses() {
	initscr();
	noecho();
	raw();
	curs_set(0);
	nodelay(stdscr, TRUE);
}

void TakedownCurses() {
	nodelay(stdscr, FALSE);
	curs_set(1);
	noraw();
	echo();
	endwin();
}

bool StartLog() {
	string log_file_name("/tmp/nh_log.txt");
	my_log.open(log_file_name);
	if (!my_log.is_open()) {
		cerr << "Could not open log file " << log_file_name << ".\n";
	}
	return my_log.is_open();
}

bool HandleOptions(int argc, char **argv) {
	int c;
	bool retval = true;
	while ((c = getopt(argc, argv, "cs:hl")) != -1) {
		switch (c) {
		case 'h':
			cout << "Usage:\n";
			cout << "-c no corridors\n";
			//cout << "-f shows the floor\n";
			cout << "-h prints this help\n";
			cout << "-l enables logging\n";
			cout << "-s specifies random seed (omit for time of day)\n";
			retval = false;
			break;

		case 'c':
			no_corridors = true;
			break;

		//case 'f':
		//	show_floor = true;
		//	break;

		case 's':
			srand((seed = atoi(optarg)));
			break;

		case 'l':
			if (!StartLog())
				return 1;
			break;
		}
	}
	return retval;
}

bool IsMovementChar(int32_t c) {
	static string movement_characters = "hjkluybnHJKLUYBN";
	return movement_characters.find(char(c)) != movement_characters.npos;
}

bool IsTransitioningBetweenCooridorAndRoom(CellBaseType a, CellBaseType b) {
	return a != b;
}

/*	This function will handle refreshing the screen as it supports the
	qualification of movement by a numeric value. By handling the update
	here, we can impose a delay (and animate the movement).
*/
void HandleMovement(Board & b, Player & p, int32_t c, int32_t numeric_qualifier) {
	Coordinate ppos = p.pos;
	CellBaseType initial_position_type = b.cells[p.pos.r][p.pos.c].base_type;

	if (isupper(c)) {
		// A capital letter movement character means RUN!
		numeric_qualifier = INT_MAX;
		// The while loop below will loop for a while and will be broken
		// when the player hits something that blocks them.
	}
	if (numeric_qualifier == 0) {
		numeric_qualifier = 1;
	}
	while (numeric_qualifier-- > 0) {
		switch (tolower(c)) {
			case 'h':		// Left
				ppos.c--;
				break;
			case 'k':		// Up
				ppos.r--;
				break;
			case 'j':		// Down
				ppos.r++;
				break;
			case 'l':
				ppos.c++;	// Right
				break;

			case 'y':		// Up / Left
				ppos.r--;
				ppos.c--;
				break;

			case 'u':		// Up / Right
				ppos.r--;
				ppos.c++;
				break;

			case 'b':		// Down / Left
				ppos.r++;
				ppos.c--;
				break;

			case 'n':		// Down / Right
				ppos.r++;
				ppos.c++;
				break;

			default:
				break;
		}

		// Should not be needed but cannot hurt.
		if (ppos.c < 0 or 
			ppos.r < 0 or 
			ppos.c >= BOARD_COLUMNS or
			ppos.r >= BOARD_ROWS
		) {
			return;
		}
		if (b.cells[ppos.r][ppos.c].base_type == ROOM or
			b.cells[ppos.r][ppos.c].base_type == CORRIDOR) {
			if (IsTransitioningBetweenCooridorAndRoom(
				initial_position_type, 
				b.cells[ppos.r][ppos.c].base_type) and
				numeric_qualifier > 0
			) {
				break;
			}
			p.pos = ppos;
			b.Display(p, show_original);
			p.Display();
			refresh();
			if (b.IsAStairway(p.pos)) {
				break;
			}
			if (numeric_qualifier > 0) {
				usleep(20000);
			}
		} else {
			break;
		}
	}
}

int main(int argc, char * argv[]) {
	srand(uint32_t(time(nullptr)));
	Board board;
	Player player;
	string digit_accumulator;
	int32_t numeric_qualifier = 0;		// 0 means none.

	if (!HandleOptions(argc, argv))
		return 0;

	InitCurses();
	InitializeCornerMap();
	int32_t c = 0;
	board.Clear();
	board.Create();
	player.pos = board.upstairs;
	if (my_log.is_open())
		my_log << "Player: " << player.pos.to_string() << endl;
	while (c != 'q') {
		if (!isdigit(c)) {
			if (digit_accumulator.size() > 0) {
				numeric_qualifier = stoi(digit_accumulator);
				digit_accumulator.clear();
			}
		} else if (isdigit(c)) {
			digit_accumulator.push_back(c);
		}
		if (c == 't')
			show_original = !show_original;
		if (c == 'r') {
down:		screen_counter++;
			board.Clear();
			board.Create();
			player.pos = board.upstairs;
			if (my_log.is_open())
				my_log << "Player: " << player.pos.to_string() << endl;
		} else if (IsMovementChar(c)) {
			HandleMovement(board, player, c, numeric_qualifier);
		} else if (c == '>') {
			if (board.IsDownstairs(player.pos)) {
				goto down;
			}
		}
		board.Display(player, show_original);
		player.Display();
		refresh();

		while (true) {
			if ((c = getch()) == 'q')
				break;
			if (c == ERR)
				usleep(50000);
			else
				break;
		}
	}

	if (my_log.is_open())
		my_log.close();
	TakedownCurses();
	return 0;
}
