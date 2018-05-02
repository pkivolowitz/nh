#pragma once
#include <curses.h>
#include <string>

class Presentation {
	public:
		Presentation();
		~Presentation();

		bool Initialize(std::string & error);
		void GetDimensions(int & l, int & c);
		void End();
				
	private:
		bool curses_is_initialized;
		WINDOW * stdscr;
		int lines;
		int cols;
};
