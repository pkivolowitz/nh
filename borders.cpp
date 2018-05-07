#include <utility>
#include <curses.h>
#include "borders.hpp"

using namespace std;

map<BorderFlags, chtype> Border::alt_charmap;

Border::Border() {
	bf = 0;
	if (alt_charmap.size() == 0) {
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RLEFT, ACS_VLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT, ACS_VLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RUP, ACS_HLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RDOWN, ACS_HLINE));

		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RLEFT_DOWN, ACS_ULCORNER));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT_DOWN, ACS_URCORNER));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RLEFT_UP, ACS_LRCORNER));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT_UP, ACS_LLCORNER));

		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT | RLEFT, ACS_VLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RUP | RDOWN, ACS_HLINE));		
	}
}
