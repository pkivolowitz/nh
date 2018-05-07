#pragma once
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
		static std::map<BorderFlags, unsigned char> alt_charmap;
		BorderFlags bf;
};
