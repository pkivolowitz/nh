#pragma once
#include <vector>

#define NOT_A_DOOR	0
#define	CLOSED_DOOR	1
#define	OPEN_DOOR	2

struct CellFlags {
	unsigned char passable : 1;
	unsigned char door : 2;
};


class Cell {
	public:
		Cell();

	private:
		CellFlags flags;
		std::vector<int> items;		// placeholder future items class.
};

class Level {
	public:
		Level();
		bool Initialize(int lines, int cols);

	private:
		std::vector<std::vector<Cell>> cells;
		int lines;
		int cols;

		static int MAX_LINES;
		static int MAX_COLS;

};
