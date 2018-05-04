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
		int GetKey();
		void End();
		void KeyMode(KeyModes km);
		void AddString(char * s, int line = 0, int col = 0, bool clear_to_eol = true, bool do_refresh = false);
		void AddString(std::string & str, int line = 0, int col = 0, bool clear_to_eol = true, bool do_refresh = false);
		void Refresh();
				
	private:
		bool curses_is_initialized;
		WINDOW * stdscr;
		int lines;
		int cols;
};
