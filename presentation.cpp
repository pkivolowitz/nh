#include <iostream>
#include <fstream>
#include <sstream>
#include "presentation.hpp"

using namespace std;

extern ofstream log;

Presentation::Presentation() {
	log << __FILE__ << " " << __FUNCTION__ << " " << __LINE__ << endl;	
	curses_is_initialized = false;
}

Presentation::~Presentation() {
	if (curses_is_initialized) {
		End();
	}
}

void Presentation::End() {
	log << __FILE__ << " " << __FUNCTION__ << " " << __LINE__ << endl;	
	if (curses_is_initialized) {
		KeyMode(KeyModes::INTERACTIVE);
		endwin();
		curses_is_initialized = false;
	}
}

bool Presentation::Initialize(string & error) {
	log << __FILE__ << " " << __FUNCTION__ << " " << __LINE__ << endl;	
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
			KeyMode(KeyModes::NONINTERACTIVE);
		}
	} else {
		error = "initscr() failed.";
	}
	return retval;
}

void Presentation::KeyMode(KeyModes km) {
	if (km == KeyModes::INTERACTIVE) {
		curs_set(1);
		echo();
		noraw();
	} else if (km == KeyModes::NONINTERACTIVE) {
		raw();
		noecho();
		curs_set(0);
	}
}

void Presentation::GetDimensions(int & l, int & c) {
	l = c = 0;
	if (curses_is_initialized) {
		l = lines;
		c = cols;
	}
}

int Presentation::GetKey(WINDOW * w) {
	if (w == nullptr)
		w = stdscr;
	return wgetch(w);
}

