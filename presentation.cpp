#include <iostream>
#include <sstream>
#include "presentation.hpp"

using namespace std;

Presentation::Presentation() {
	curses_is_initialized = false;
}

Presentation::~Presentation() {
	if (curses_is_initialized) {
		endwin();
	}
}

bool Presentation::Initialize(string & error) {
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
			curses_is_initialized = true;
		}
	} else {
		error = "initscr() failed.";
	}
	return retval;
}

