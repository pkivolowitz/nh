#pragma once
#include <vector>

#include "floor_manager.hpp"
#include "presentation.hpp"
#include "coordinate.hpp"
#include "borders.hpp"

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
		virtual chtype Symbol();
		void Push(ItemPtr);
		ItemPtr Pop();
		bool IsVisible();
		void SetVisibility(bool);
		BaseType BT();

	protected:
		CellFlags flags;
		FloorManager fl;
		BaseType bt;
		static const chtype base_type_symbols[3];
};

typedef Cell * CellPtr;

class Rock : public Cell {
public:
	Rock();
	virtual ~Rock();
	chtype Symbol();
	void SetSymbol(chtype c);

private:
	chtype symbol;
};

typedef Rock * RockPtr;

class Floor : public Cell {
	public:
		Floor();
		Floor(int room_number);
		virtual ~Floor();
		void SetRoomNumber(int room_number);
		int GetRoomNumber();

	protected:
		int room_number;
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
		bool Initialize(Presentation * p);
		void Render(Presentation * p);
		void Replace(int l, int c, CellPtr cell);

	private:
		void CalculateVisibility();
		std::vector<Cell *> cells;
		int lines;
		int cols;
		int Offset(int l, int c);
		int Offset(Coordinate c);
		void CalcRoomBoundaries(Coordinate & tl, Coordinate & br, Presentation * p);
		void FillRoomBoundaries(Coordinate & tl, Coordinate & br, std::vector<Coordinate> & v, int room_number);
		void FlattenRoom(std::vector<Coordinate> & v, int room_number);
		void CheckFloor(Coordinate & c, std::vector<Coordinate> & v, int room_number);
		void AddBorders();
		BorderFlags EvaluateBorder(Coordinate & center);
		static const int MAX_ROOMS = 9;
		static const int MIN_ROOM_WIDTH = 2;
		static const int MIN_ROOM_HEIGHT = 2;
		static const int MAX_ROOM_WIDTH_RAND = 9;
		static const int MAX_ROOM_HEIGHT_RAND = 5;
};

class HallwayGenerator {
	public:
		HallwayGenerator();
		void GenerateHallways(Level * l);
};

