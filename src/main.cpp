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
bool show_floor = false;

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
	while ((c = getopt(argc, argv, "s:hlf")) != -1) {
		switch (c) {
		case 'h':
			cout << "Usage:\n";
			cout << "-f shows the floor\n";
			cout << "-h prints this help\n";
			cout << "-l enables logging\n";
			cout << "-s specifies random seed (omit for time of day)\n";
			retval = false;
			break;

		case 'f':
			show_floor = true;
			break;

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
	static string movement_characters = "hjkluybn";

	return movement_characters.find(char(c)) != movement_characters.npos;
}

void HandleMovement(Board & b, Player & p, int32_t c) {
	Coordinate ppos = p.pos;
	switch (c) {
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
		p.pos = ppos;
	}
}

int main(int argc, char * argv[]) {
	srand(uint32_t(time(nullptr)));
	Board board;
	Player player;

	if (!HandleOptions(argc, argv))
		return 0;

	InitCurses();
	InitializeCornerMap();
	int32_t c = 0;
	bool show_original = false;
	board.Clear();
	board.Create();
	player.pos = board.upstairs;
	if (my_log.is_open())
		my_log << "Player: " << player.pos.to_string() << endl;
	while (c != 'q') {
		if (c == 't')
			show_original = !show_original;
		if (c == 'R') {
			screen_counter++;
			board.Clear();
			board.Create();
			player.pos = board.upstairs;
			if (my_log.is_open())
				my_log << "Player: " << player.pos.to_string() << endl;
		} else if (IsMovementChar(c)) {
			HandleMovement(board, player, c);
		}
		board.Display(show_original);
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
