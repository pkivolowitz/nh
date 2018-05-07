#pragma once
#include <curses.h>

class Item {
	public:
		Item();

		chtype Symbol();

	private:
		chtype symbol;
};

typedef Item * ItemPtr;
