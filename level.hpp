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
	FLOOR 
};

class Cell {
	public:
		Cell();
		virtual ~Cell();
		char Symbol();
		void Push(ItemPtr);
		ItemPtr Pop();
		bool IsVisible();
		void SetVisibility(bool);

	protected:
		CellFlags flags;
		FloorManager fl;
		BaseType bt;
		static const char * base_type_symbols;
};

typedef Cell * CellPtr;

class Rock : public Cell {
public:
	Rock();
	virtual ~Rock();
};

typedef Rock * RockPtr;

class Floor : public Cell {
	public:
		Floor();
		virtual ~Floor();
};

typedef Floor * FloorPtr;

class Hallway : public Cell {
	public:
		Hallway();
		virtual ~Hallway();

	private:
};

typedef Hallway * HallwayPtr;

class Level {
	public:
		Level();
		~Level();
		bool Initialize(int lines, int cols);
		void Render(Presentation * p);
		void Replace(int l, int c, CellPtr cell);

	private:
		void CalculateVisibility();
		std::vector<Cell *> cells;
		int lines;
		int cols;
		int Offset(int l, int c);
};
