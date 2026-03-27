// Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

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
#include <memory>
#include "game_time.hpp"
#include "drawing_support.hpp"
#include "cell.hpp"
#include "coordinate.hpp"
#include "utilities.hpp"
#include "room.hpp"
#include "board.hpp"
#include "player.hpp"
#include "colors.hpp"
#include "cmd_line_options.hpp"
#include "config.hpp"

using namespace std;

int32_t seed = 0;
int32_t turn_counter = 0;
uint32_t current_board = 0;
CursesColorSupport ccs;

bool no_corridors = false;
bool show_original = false;

// Sidebar detail mode: toggled by 'i' to show item weights/types.
bool detail_mode = false;

ofstream my_log;

// Minimum terminal width to accommodate map (80) + gap (1) + sidebar.
static const int32_t MIN_TERMINAL_COLS = 120;

// Map window dimensions: info line + board + two status lines.
static const int32_t MAP_WIN_ROWS = BOARD_TOP_OFFSET + BOARD_ROWS + 2;
static const int32_t MAP_WIN_COLS = BOARD_COLUMNS;

// Gap between map and sidebar.
static const int32_t SIDEBAR_GAP = 1;

// Initialize ncurses and the game's shared color palette.
void InitCurses() {
	initscr();
	ccs.Initialize();
	standend();
	noecho();
	raw();
	curs_set(0);
}

// Restore terminal settings before exiting.
void TakedownCurses() {
	curs_set(1);
	noraw();
	echo();
	endwin();
}

// Open the optional debug log file in /tmp.
bool StartLog() {
	string log_file_name("/tmp/nh_log.txt");
	my_log.open(log_file_name);
	if (!my_log.is_open()) {
		cerr << "Could not open log file " << log_file_name << ".\n";
	}
	return my_log.is_open();
}

// Report whether a key is one of the supported movement commands.
bool IsMovementChar(int32_t c) {
	static string movement_characters = "hjkluybnHJKLUYBN";
	return movement_characters.find(char(c)) != movement_characters.npos;
}

// Report whether moving between these cell types crosses a boundary.
bool IsTransitioningBetweenCooridorAndRoom(CellBaseType a, CellBaseType b) {
	return a != b;
}

// Convert a vi-key movement character to a (dr, dc) offset.
// Returns false if the key is not a valid direction.
// Convert a movement key into row and column deltas.
bool DirectionFromKey(int32_t key, int32_t & dr, int32_t & dc) {
	dr = dc = 0;
	switch (tolower(key)) {
		case 'h': dc = -1; break;
		case 'l': dc =  1; break;
		case 'k': dr = -1; break;
		case 'j': dr =  1; break;
		case 'y': dr = -1; dc = -1; break;
		case 'u': dr = -1; dc =  1; break;
		case 'b': dr =  1; dc = -1; break;
		case 'n': dr =  1; dc =  1; break;
		default: return false;
	}
	return true;
}

/*	This function will handle refreshing the screen as it supports the
	qualification of movement by a numeric value. By handling the update
	here, we can impose a delay (and animate the movement).
*/
void HandleMovement(Board * b, Player & p, int32_t c, int32_t numeric_qualifier) {
	Coordinate ppos = p.pos;

	if (isupper(c)) {
		// A capital letter movement character means RUN!
		numeric_qualifier = INT_MAX;
	}

	if (numeric_qualifier == 0) {
		numeric_qualifier = 1;
	}

	bool first_step = true;
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

		if (ppos.c < 0 or ppos.r < 0 or
			ppos.c >= BOARD_COLUMNS or ppos.r >= BOARD_ROWS
		) {
			return;
		}

		// We've run into a wall, corner, or closed door.
		if (!b->IsNavigable(ppos)) {
			if (b->IsDoor(ppos)) {
				b->ClearInfoLine();
				Cell & door_cell = b->cells[ppos.r][ppos.c];
				const char * msg = nullptr;
				switch (door_cell.door_state) {
					case DOOR_CLOSED: msg = "The door is closed."; break;
					case DOOR_LOCKED: msg = "This door is locked."; break;
					case DOOR_STUCK:  msg = "The door is stuck!"; break;
					default: break;
				}
				if (msg) {
					mvwaddstr(b->win, 0, 0, msg);
					b->UpdateTime();
				}
			}
			break;
		}

		CellBaseType current = b->cells[p.pos.r][p.pos.c].base_type;
		CellBaseType next = b->cells[ppos.r][ppos.c].base_type;

		// Doors behave as corridors for transition purposes.
		if (current == DOOR) current = CORRIDOR;
		if (next == DOOR) next = CORRIDOR;

		// The current and next cells are of different base_type. For
		// example, (CORRIDOR and ROOM) or (ROOM and CORRIDOR). If this
		// is not our first step, then cause the number of additional
		// steps to be taken to be 0 AND make sure our last position is
		// the hallway and not the room.
		if (current != next and !first_step) {
			numeric_qualifier = 0;
			if (current == ROOM)
				p.pos = ppos;
		} else {
			p.pos = ppos;
		}

		turn_counter++;
		b->Display(p, show_original);
		p.Display(b->win);
		wrefresh(b->win);

		// Stop running if the current position is a stairway.
		if (b->IsAStairway(p.pos)) {
			break;
		}

		// Stop running at doors — even open ones are notable.
		if (b->IsDoor(p.pos)) {
			break;
		}

		// Stop running if the current position holds a goodie.
		if (b->GetSymbol(ppos) >= 0) {
			break;
		}

		if (numeric_qualifier > 0) {
			usleep(20000);
		}
		first_step = false;
	}
}

// Render the sidebar: inventory + dungeon level.
void RenderSidebar(WINDOW * sidebar_win, Player & player, int32_t sidebar_rows) {
	werase(sidebar_win);
	player.RenderSidebar(sidebar_win, detail_mode);

	// Dungeon level at the very bottom of the sidebar.
	stringstream dl;
	dl << "Dlvl:" << current_board + 1;
	mvwaddstr(sidebar_win, sidebar_rows - 1, 1, dl.str().c_str());

	wrefresh(sidebar_win);
}

// Run the main game loop, including input, movement, and rendering.
int main(int argc, char * argv[]) {
	srand(uint32_t(time(nullptr)));

	vector<Board *> boards;
	Board * board;

	// Load config from ~/.pnhrc before command-line parsing so
	// that -n on the command line can override the config name.
	GameConfig config;
	config.Load();

	Player player;
	player.name      = config.name;
	player.role      = config.role;
	player.race      = config.race;
	player.alignment = config.alignment;

	string digit_accumulator;
	int32_t numeric_qualifier = 0;		// 0 means none.

	if (!HandleOptions(argc, argv, player.name))
		return 0;

	InitCurses();

	// Enforce minimum terminal width for the sidebar layout.
	int32_t term_cols;
	{
		int32_t rows;
		getmaxyx(stdscr, rows, term_cols);
		(void)rows;
	}
	if (term_cols < MIN_TERMINAL_COLS) {
		TakedownCurses();
		cerr << "Terminal must be at least " << MIN_TERMINAL_COLS
			 << " columns wide (currently " << term_cols << ").\n";
		return 1;
	}

	// Create the map window (left side) and sidebar window (right side).
	WINDOW * map_win = newwin(MAP_WIN_ROWS, MAP_WIN_COLS, 0, 0);
	int32_t sidebar_cols = term_cols - MAP_WIN_COLS - SIDEBAR_GAP;
	int32_t sidebar_rows = MAP_WIN_ROWS;
	WINDOW * sidebar_win = newwin(sidebar_rows, sidebar_cols,
								  0, MAP_WIN_COLS + SIDEBAR_GAP);

	// Use timeout-based input on the map window: wgetch waits up to
	// 50ms then returns ERR if no key is available.
	wtimeout(map_win, 50);
	keypad(map_win, TRUE);

	InitializeCornerMap();

	board = new Board();
	board->win = map_win;
	boards.push_back(board);

	int32_t c = 0;
	player.pos = board->upstairs;
	if (my_log.is_open())
		my_log << "Player: " << player.pos.to_string() << endl;

	while (c != 'q') {
		// Numeric qualifier accumulation: digits build a string
		// that qualifies the next movement command.
		if (!isdigit(c)) {
			if (!digit_accumulator.empty()) {
				numeric_qualifier = stoi(digit_accumulator);
				digit_accumulator.clear();
			}
		} else {
			digit_accumulator.push_back(c);
		}

		if (c == 't') {
			show_original = !show_original;

		} else if (IsMovementChar(c)) {
			HandleMovement(board, player, c, numeric_qualifier);

		} else if (c == '>' and board->IsDownstairs(player.pos)) {
			turn_counter++;
			if (current_board == boards.size() - 1) {
				board = new Board();
				board->win = map_win;
				boards.push_back(board);
				current_board++;
			} else {
				current_board++;
				board = boards.at(current_board);
			}
			player.pos = board->upstairs;

		} else if (c == '<') {
			// Go up if on an upward staircase and not on level 0.
			if (board->IsUpstairs(player.pos) and current_board > 0) {
				turn_counter++;
				current_board--;
				board = boards.at(current_board);
				player.pos = board->downstairs;
			}

		} else if (c == 'i') {
			// Toggle inventory detail mode.
			detail_mode = !detail_mode;

		} else if (c == ',') {
			// Pickup: move all items from the floor into inventory.
			auto items = board->RemoveGoodies(player.pos);
			if (!items.empty()) {
				int32_t picked_up = 0;
				bool full = false;
				for (auto & item : items) {
					if (full) {
						board->AddGoodie(player.pos, std::move(item));
						continue;
					}
					char letter = player.AddToInventory(item);
					if (letter == 0) {
						full = true;
						board->AddGoodie(player.pos, std::move(item));
					} else {
						picked_up++;
					}
				}
				if (picked_up > 0) {
					turn_counter++;
				}
				// Report what happened on the info line.
				board->ClearInfoLine();
				if (full) {
					mvwaddstr(board->win, 0, 0,
							  "Your pack cannot hold any more.");
				} else {
					stringstream ss;
					ss << "Picked up " << picked_up
					   << (picked_up > 1 ? " items." : " item.");
					mvwaddstr(board->win, 0, 0, ss.str().c_str());
				}
				board->UpdateTime();
			}

		} else if (c == 'd') {
			// Drop: prompt for inventory letter, return item to floor.
			if (player.InventoryCount() > 0) {
				board->ClearInfoLine();
				mvwaddstr(board->win, 0, 0, "Drop what? ");
				board->UpdateTime();
				wrefresh(board->win);

				// Block until the player presses a letter or ESC.
				wtimeout(board->win, -1);
				int32_t letter = wgetch(board->win);
				wtimeout(board->win, 50);

				if (letter != 27) {		// 27 = ESC cancels
					auto item = player.RemoveFromInventory(letter);
					if (item) {
						board->ClearInfoLine();
						stringstream ss;
						ss << "Dropped " << item->item_name << ".";
						mvwaddstr(board->win, 0, 0, ss.str().c_str());
						board->UpdateTime();
						board->AddGoodie(player.pos, std::move(item));
						turn_counter++;
					} else {
						board->ClearInfoLine();
						mvwaddstr(board->win, 0, 0,
								  "You don't have that.");
						board->UpdateTime();
					}
				} else {
					board->ClearInfoLine();
				}
			}

		} else if (c == 'o' || c == 'c') {
			// Open (o) or Close (c) a door in an adjacent cell.
			bool opening = (c == 'o');
			board->ClearInfoLine();
			mvwaddstr(board->win, 0, 0,
				opening ? "Open in what direction? "
						: "Close in what direction? ");
			board->UpdateTime();
			wrefresh(board->win);

			wtimeout(board->win, -1);
			int32_t dir = wgetch(board->win);
			wtimeout(board->win, 50);

			int32_t dr, dc;
			if (dir == 27) {
				// ESC cancels.
				board->ClearInfoLine();
			} else if (DirectionFromKey(dir, dr, dc)) {
				Coordinate target(player.pos.r + dr, player.pos.c + dc);
				string msg = opening
					? board->TryOpenDoor(target)
					: board->TryCloseDoor(target);
				board->ClearInfoLine();
				mvwaddstr(board->win, 0, 0, msg.c_str());
				board->UpdateTime();
				// Opening/closing a door costs a turn.
				if (msg.find("You ") == 0) {
					turn_counter++;
				}
			} else {
				board->ClearInfoLine();
				mvwaddstr(board->win, 0, 0, "Invalid direction.");
				board->UpdateTime();
			}
		}

		// Full frame render.
		board->Display(player, show_original);
		player.Display(board->win);
		if (board->GetSymbol(player.pos) >= 0) {
			board->ReportGoodies(player.pos);
		}
		wrefresh(board->win);
		RenderSidebar(sidebar_win, player, sidebar_rows);

		// Reset numeric qualifier after each command.
		numeric_qualifier = 0;

		// Poll the keyboard. wgetch refreshes the map window
		// internally before checking for input.
		while (true) {
			c = wgetch(map_win);
			if (c == ERR) {
				board->UpdateTime();
				wrefresh(map_win);
			} else {
				break;
			}
		}
	}

	while (!boards.empty()) {
		board = boards.back();
		delete board;
		boards.pop_back();
	}
	delwin(sidebar_win);
	delwin(map_win);
	if (my_log.is_open())
		my_log.close();
	TakedownCurses();
	return 0;
}
