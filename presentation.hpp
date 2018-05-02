#pragma once
#include <curses.h>
#include <string>

class Presentation {
	public:
		Presentation();
		bool Initialize(std::string & error);
		~Presentation();

	private:
		bool curses_is_initialized;
		WINDOW * stdscr;
		int lines;
		int cols;
};
