#pragma once
#include <curses.h>
#include <string>

enum KeyModes {
	KM_RAW 		= 0x0001,
	KM_NOECHO 	= 0x0002,
	KM_NOCURS	= 0x0004,
	KM_NODELAY	= 0x0008
};

#define KM_NONINTERACTIVE		(KM_RAW | KM_NOECHO | KM_NOCURS | KM_NODELAY)
#define KM_INTERACTIVE			(0)

class Presentation {
	public:
		Presentation();
		~Presentation();

		bool Initialize(std::string & error);
		void GetDimensions(int & l, int & c);
		int GetKey();
		void End();
		void KeyMode(unsigned int km);
		void AddString(char * s, int line = 0, int col = 0, bool clear_to_eol = true, bool do_refresh = false);
		void AddString(std::string & str, int line = 0, int col = 0, bool clear_to_eol = true, bool do_refresh = false);
		void Refresh();
				
	private:
		bool curses_is_initialized;
		WINDOW * stdscr;
		int lines;
		int cols;
};
