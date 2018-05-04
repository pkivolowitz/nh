#pragma once
#include <curses.h>
#include <string>

enum class KeyModes {
	INTERACTIVE,
	NONINTERACTIVE
};

class Presentation {
	public:
		Presentation();
		~Presentation();

		bool Initialize(std::string & error);
		void GetDimensions(int & l, int & c);
		int GetKey(WINDOW * w = nullptr);
		void End();
		void KeyMode(KeyModes km);
				
	private:
		bool curses_is_initialized;
		WINDOW * stdscr;
		int lines;
		int cols;
};
