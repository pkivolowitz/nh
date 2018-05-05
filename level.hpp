#pragma once
#include <vector>

#include "floor_manager.hpp"
#include "presentation.hpp"

/*	CellFlags describes attributes of cells for which there can be only one. 
	For example:
		- is what is in this cell make it *impossible* to traverse?
		- there can be at most one door.
		- does this cell block line of sight?
*/

struct CellFlags {
	unsigned char passable : 1;
	unsigned char door : 2;
	unsigned char blocks_line_of_sight : 1;
	unsigned char is_visible : 1;
};

enum {
	DOOR_NOT,
	DOOR_OPEN,
	DOOR_CLOSED
};

enum class BaseType {
	ROCK,
	HALLWAY,
	ROOM 
};

class Cell {
	public:
		Cell();
		char Symbol();
		void Push(ItemPtr);
		ItemPtr Pop();
		bool IsVisible();
		void SetVisibility(bool);

	protected:
		CellFlags flags;
		FloorManager fl;
		BaseType bt;
};

class Rock : public Cell {
public:
	Rock();
};

class Room : public Cell {
	public:
		Room();

	private:
		int room_number;
};

class Level {
	public:
		Level();
		~Level();
		bool Initialize(int lines, int cols);
		void Render(Presentation * p);

	private:
		void CalculateVisibility();
		std::vector<Cell *> cells;
		int lines;
		int cols;
		int Offset(int l, int c);
};
