#include <iostream>
#include <fstream>
#include <sstream>
#include "presentation.hpp"
#include "logging.hpp"

using namespace std;

Presentation::Presentation() {
	curses_is_initialized = false;
}

Presentation::~Presentation() {
	if (curses_is_initialized) {
		End();
	}
}

void Presentation::End() {
	ENTERING();
	if (curses_is_initialized) {
		KeyMode(KM_INTERACTIVE);
		endwin();
		curses_is_initialized = false;
	}
	LEAVING();
}

bool Presentation::Initialize(string & error) {
	ENTERING();
	bool retval = false;
	error = "";
	if (curses_is_initialized) {
		error = "attempt to initialize curses more than once.";
	} else if ((this->stdscr = initscr()) != nullptr) {
		lines = LINES;
		cols = COLS;
		if (lines < 24 || cols < 80) {
			endwin();
			this->stdscr = nullptr;
			error = "console window is not large enough.";
		} else {
			retval = true;
			lines = 24;
			cols = 80;
			curses_is_initialized = true;
			KeyMode(KM_NONINTERACTIVE);
		}
	} else {
		error = "initscr() failed.";
	}
	RETURNING(retval);
	return retval;
}

void Presentation::KeyMode(unsigned int km) {
	assert(curses_is_initialized);
	curs_set((km & KM_NOCURS) ? 0 : 1);
	nodelay(stdscr, (km & KM_NODELAY) ? TRUE : FALSE);
	(km & KM_NOECHO) ? noecho() : echo();
	(km & KM_RAW) ? raw() : noraw();
}

void Presentation::GetDimensions(int & l, int & c) {
	assert(curses_is_initialized);
	l = c = 0;
	if (curses_is_initialized) {
		l = lines;
		c = cols;
	}
}

void Presentation::Refresh() {
	refresh();
}

void Presentation::AddString(string & str, int line, int col, bool clear_to_eol, bool do_refresh) {
	AddString((char *) str.c_str(), line, col, clear_to_eol, do_refresh);
}

void Presentation::AddString(char * s, int line, int col, bool clear_to_eol, bool do_refresh) {
	wmove(stdscr, line, col);
	if (clear_to_eol)
		clrtoeol();
	if (s != nullptr)
		addstr(s);
	if (do_refresh)
		refresh();
}

int Presentation::GetKey() {
	assert(curses_is_initialized);
	return getch();
}

