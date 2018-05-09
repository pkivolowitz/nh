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
		void AddCh(chtype c);
		void Refresh();
		void ClearMapArea();
		void Move(int l, int c);
		static const int COMMAND_LINES = 1;		// lines reserved at top of screen
		static const int STATUS_LINES = 2;		// lines reserved at bottom of screen
		static const int MAX_LINES = 24;		// assumed logical lines in screen
		static const int MAX_COLS = 80;			// assumed logical columns in screen

		static const int TOP_DRAWABLE_LINE  = COMMAND_LINES;
		static const int BOT_DRAWABLE_LINE  = MAX_LINES - STATUS_LINES - 1;
		static const int LEFT_DRAWABLE_COL  = 0;
		static const int RIGHT_DRAWABLE_COL = MAX_COLS - 1;
		static const int DRAWABLE_LINES = MAX_LINES - COMMAND_LINES - STATUS_LINES;
		static const int DRAWABLE_COLS = MAX_COLS;

	private:
		bool curses_is_initialized;
		WINDOW * stdscr;
		int lines;
		int cols;
};
