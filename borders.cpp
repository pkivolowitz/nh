#include <utility>
#include <curses.h>
#include "borders.hpp"

using namespace std;

map<BorderFlags, chtype> Border::alt_charmap;

Border::Border() {
	if (alt_charmap.size() == 0) {
		
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RLEFT, ACS_VLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT, ACS_VLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RUP, ACS_HLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RDOWN, ACS_HLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RLEFT_DOWN, ACS_URCORNER));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT_DOWN, ACS_ULCORNER));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RLEFT_UP, ACS_LRCORNER));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT_UP, ACS_LLCORNER));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT | RLEFT, ACS_VLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RUP | RDOWN, ACS_HLINE));		
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RLEFT | RLEFT_UP | RLEFT_DOWN, ACS_VLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RLEFT | RLEFT_DOWN, ACS_VLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RLEFT | RLEFT_UP, ACS_VLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RLEFT | RLEFT_UP | RLEFT_DOWN | RRIGHT_UP | RRIGHT, ACS_VLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT | RRIGHT_DOWN | RLEFT | RLEFT_UP | RLEFT_DOWN, ACS_VLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT | RRIGHT_UP | RRIGHT_DOWN | RLEFT_UP, ACS_RTEE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RLEFT | RLEFT_UP | RLEFT_DOWN | RRIGHT_DOWN, ACS_LTEE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RDOWN | RLEFT_DOWN | RRIGHT_DOWN | RRIGHT_UP, ACS_BTEE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RUP | RLEFT_UP | RRIGHT_UP | RLEFT_DOWN, ACS_TTEE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT | RRIGHT_UP | RRIGHT_DOWN, ACS_VLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT | RRIGHT_DOWN, ACS_VLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT | RRIGHT_UP, ACS_VLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RLEFT | RLEFT_UP | RRIGHT_UP, ACS_LTEE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RLEFT | RLEFT_DOWN | RRIGHT_DOWN, ACS_LTEE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RLEFT | RLEFT_UP | RLEFT_DOWN | RUP | RRIGHT_UP | RDOWN, ACS_HLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT | RLEFT_UP | RLEFT_DOWN | RUP | RRIGHT_UP | RRIGHT_DOWN | RDOWN, ACS_HLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT | RRIGHT_UP | RRIGHT_DOWN | RUP, ACS_URCORNER));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RLEFT | RLEFT_UP | RLEFT_DOWN | RUP | RRIGHT_UP, ACS_ULCORNER));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT | RRIGHT_UP | RRIGHT_DOWN | RDOWN | RLEFT_DOWN, ACS_LRCORNER));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT | RRIGHT_DOWN | RDOWN, ACS_LRCORNER));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RUP | RLEFT_UP | RRIGHT_UP | RRIGHT, ACS_URCORNER));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RLEFT | RLEFT_UP | RLEFT_DOWN | RDOWN | RRIGHT_DOWN, ACS_LLCORNER));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RLEFT | RLEFT_DOWN | RDOWN, ACS_LLCORNER));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RLEFT | RLEFT_UP | RUP, ACS_ULCORNER));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RUP | RLEFT_UP | RRIGHT_UP | RLEFT, ACS_ULCORNER));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RDOWN | RLEFT_DOWN | RRIGHT_DOWN | RRIGHT, ACS_LRCORNER));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RDOWN | RLEFT_DOWN | RRIGHT_DOWN | RLEFT, ACS_LLCORNER));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RUP | RRIGHT_UP | RRIGHT, ACS_URCORNER));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RDOWN | RRIGHT_UP | RRIGHT | RRIGHT_DOWN, ACS_LRCORNER));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT_UP | RRIGHT | RDOWN | RLEFT_DOWN, ACS_LRCORNER));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT_UP | RUP | RLEFT | RLEFT_DOWN, ACS_ULCORNER));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RUP | RLEFT_UP | RRIGHT_UP, ACS_HLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RUP | RRIGHT_UP, ACS_HLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RUP | RLEFT_UP, ACS_HLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RUP | RLEFT_UP | RRIGHT_UP | RLEFT | RLEFT_DOWN | RDOWN | RRIGHT_DOWN, ACS_HLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RUP | RLEFT_UP | RLEFT_DOWN | RDOWN | RRIGHT_DOWN, ACS_HLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RUP | RLEFT_UP | RRIGHT_UP | RDOWN | RRIGHT_DOWN, ACS_HLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RUP | RLEFT_UP | RRIGHT_UP | RDOWN | RLEFT_DOWN, ACS_HLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RUP | RLEFT_UP | RLEFT | RLEFT_DOWN, ACS_ULCORNER));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RUP | RLEFT_UP | RRIGHT | RRIGHT_DOWN, ACS_URCORNER));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RLEFT | RLEFT_UP | RDOWN | RRIGHT_DOWN, ACS_LLCORNER));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RLEFT_UP | RRIGHT_UP | RRIGHT | RLEFT, ACS_VLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RDOWN | RLEFT_DOWN | RRIGHT_DOWN, ACS_HLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RDOWN | RLEFT_DOWN | RRIGHT_DOWN | RUP | RLEFT_UP | RRIGHT_UP, ACS_HLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RDOWN | RLEFT_DOWN | RUP | RLEFT_UP, ACS_HLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RDOWN | RRIGHT_DOWN, ACS_HLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RDOWN | RLEFT_DOWN, ACS_HLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RDOWN | RLEFT_DOWN | RRIGHT_DOWN | RUP | RRIGHT_UP, ACS_HLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT_UP | RLEFT_DOWN | RDOWN, ACS_BTEE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT_UP | RLEFT_DOWN | RUP, ACS_TTEE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT_UP | RLEFT_UP, ACS_BTEE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT_UP | RRIGHT_DOWN | RDOWN, ACS_BTEE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT_UP | RLEFT_DOWN, ACS_PLUS));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT_DOWN | RLEFT_UP, ACS_PLUS));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RLEFT | RLEFT_UP | RLEFT_DOWN | RRIGHT_UP, ACS_LTEE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT | RRIGHT_DOWN | RLEFT_DOWN, ACS_RTEE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RLEFT_DOWN | RLEFT_UP, ACS_RTEE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT | RRIGHT_UP | RRIGHT_DOWN | RLEFT_DOWN, ACS_RTEE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT | RLEFT_UP | RRIGHT_UP, ACS_RTEE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RLEFT_UP | RLEFT_DOWN | RDOWN | RRIGHT_DOWN, ACS_BTEE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT_UP | RRIGHT_DOWN | RLEFT_UP | RUP, ACS_TTEE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RLEFT_DOWN | RLEFT_UP | RUP, ACS_TTEE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT | RRIGHT_UP | RLEFT | RLEFT_DOWN, ACS_VLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT | RRIGHT_UP | RRIGHT_DOWN | RLEFT | RLEFT_DOWN, ACS_VLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT | RRIGHT_UP | RRIGHT_DOWN | RLEFT | RLEFT_UP, ACS_VLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT | RRIGHT_UP | RRIGHT_DOWN | RLEFT_UP | RLEFT | RLEFT_DOWN, ACS_VLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT | RRIGHT_UP | RRIGHT_DOWN | RLEFT_UP | RUP, ACS_URCORNER));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT_UP | RRIGHT | RLEFT | RLEFT_DOWN | RDOWN | RRIGHT_DOWN, ACS_VLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT | RLEFT | RLEFT_DOWN | RRIGHT_DOWN | RDOWN | RLEFT_UP, ACS_VLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RLEFT | RLEFT_DOWN | RLEFT_UP | RDOWN, ACS_LLCORNER));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RLEFT_UP | RLEFT_DOWN | RDOWN, ACS_BTEE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT | RRIGHT_UP | RRIGHT_DOWN | RUP | RLEFT_UP | RLEFT | RLEFT_DOWN, ACS_VLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT | RRIGHT_UP | RRIGHT_DOWN | RDOWN | RLEFT_UP | RLEFT | RLEFT_DOWN, ACS_VLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT | RRIGHT_DOWN | RLEFT | RLEFT_DOWN, ACS_VLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT_DOWN | RLEFT_DOWN, ACS_TTEE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT_DOWN | RRIGHT_UP, ACS_LTEE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RDOWN | RUP | RRIGHT_DOWN | RRIGHT_UP, ACS_HLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RLEFT | RRIGHT | RRIGHT_DOWN | RLEFT_UP, ACS_VLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RUP | RDOWN | RRIGHT_UP | RLEFT_DOWN, ACS_HLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RUP | RDOWN | RRIGHT_DOWN | RLEFT_UP, ACS_HLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RUP | RLEFT_UP | RRIGHT_DOWN, ACS_TTEE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RDOWN | RLEFT_UP | RRIGHT_DOWN, ACS_BTEE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RUP | RRIGHT_UP | RRIGHT_DOWN, ACS_TTEE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RLEFT_UP | RLEFT_DOWN | RDOWN | RRIGHT_DOWN | RRIGHT | RRIGHT_UP, ACS_LRCORNER));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RLEFT_UP | RLEFT | RUP | RDOWN | RRIGHT_DOWN | RRIGHT | RRIGHT_UP, ACS_HLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RLEFT_UP | RLEFT | RLEFT_DOWN | RUP | RRIGHT | RRIGHT_UP, ACS_VLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RLEFT_UP | RLEFT | RLEFT_DOWN | RDOWN | RRIGHT | RRIGHT_UP, ACS_VLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RLEFT_DOWN | RRIGHT | RRIGHT_UP, ACS_LRCORNER));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RLEFT_DOWN | RLEFT | RRIGHT_UP, ACS_ULCORNER));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RUP | RDOWN | RLEFT | RLEFT_UP | RRIGHT_DOWN, ACS_HLINE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RUP | RLEFT | RLEFT_UP | RLEFT_DOWN | RRIGHT_UP | RRIGHT_DOWN, ACS_ULCORNER));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RLEFT | RLEFT_UP | RRIGHT_DOWN, ACS_LTEE));
		Border::alt_charmap.insert(pair<BorderFlags, chtype>(RRIGHT | RLEFT_UP | RRIGHT_DOWN, ACS_RTEE));
	}
}
