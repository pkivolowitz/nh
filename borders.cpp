#include <utility>
#include <curses.h>
#include "borders.hpp"

using namespace std;

map<BorderFlags, unsigned char> Border::alt_charmap;

Border::Border() {
	bf = 0;
	if (alt_charmap.size() == 0) {
		Border::alt_charmap.insert(pair<BorderFlags, unsigned char>(RLEFT, ACS_VLINE));
		Border::alt_charmap.insert(pair<BorderFlags, unsigned char>(RRIGHT, ACS_VLINE));
		Border::alt_charmap.insert(pair<BorderFlags, unsigned char>(RUP, ACS_HLINE));
		Border::alt_charmap.insert(pair<BorderFlags, unsigned char>(RDOWN, ACS_HLINE));

		Border::alt_charmap.insert(pair<BorderFlags, unsigned char>(RLEFT_DOWN, ACS_ULCORNER));
		Border::alt_charmap.insert(pair<BorderFlags, unsigned char>(RRIGHT_DOWN, ACS_URCORNER));
		Border::alt_charmap.insert(pair<BorderFlags, unsigned char>(RLEFT_UP, ACS_LRCORNER));
		Border::alt_charmap.insert(pair<BorderFlags, unsigned char>(RRIGHT_UP, ACS_LLCORNER));

		Border::alt_charmap.insert(pair<BorderFlags, unsigned char>(RRIGHT | RLEFT, ACS_VLINE));
		Border::alt_charmap.insert(pair<BorderFlags, unsigned char>(RUP | RDOWN, ACS_HLINE));		
	}
}
