#pragma once
#include <curses.h>
#include <map>

#define	RLEFT		0x01
#define	RRIGHT		0x02
#define	RUP			0x04
#define RDOWN		0x08
#define	RLEFT_UP	0x10
#define	RLEFT_DOWN	0x20
#define	RRIGHT_UP	0x40
#define	RRIGHT_DOWN	0x80

typedef unsigned char BorderFlags;

class Border {
	public:
		Border();
		static std::map<BorderFlags, chtype> alt_charmap;
		static bool IsCorner(chtype);
		static bool IsBadForEastWest(chtype);
		static bool IsBadForNorthSouth(chtype);
		static bool IsEastWest(chtype c) { return c == ACS_HLINE; }
		static bool IsNorthSouth(chtype c) { return c == ACS_VLINE; }
		static bool IsWall(chtype c);
		static bool IsBorder(chtype c);
};
