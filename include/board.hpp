#pragma once
#include <cinttypes>
#include <vector>
#include <string>
#include "utilities.hpp"
#include "cell.hpp"
#include "room.hpp"

using ivec = std::vector<int32_t>;

struct Board {
	Cell cells[BOARD_ROWS][BOARD_COLUMNS];
	void Clear();
	void Create();
	void Display(bool show_original);
	bool IsDownstairs(Coordinate & c);
	bool IsUpstairs(Coordinate & c);

	Coordinate upstairs;
	Coordinate downstairs;

	RoomVec rooms;

private:
	std::string BuildCornerKey(int32_t r, int32_t c);
	void FindRowsToAvoid(ivec &r_avoid);
	void FindColsToAvoid(ivec &c_avoid);
	void FindGCoords(ivec &br, ivec &bc, Room &r, Coordinate &coord);
	void Fill(int32_t rn);
	void Enclose(int32_t rn);
	void PlaceCorners();
	void PlaceCorridors();
	void PlaceStairs();
	Coordinate GetGoodStairLocation(Room & room);
	void RemoveFloorDigits();
	bool PlanBForCooridors(uint32_t room_index);
	void FlattenRooms();
	void LayCorridor(Coordinate &, Coordinate &);
	bool IsAStairway(Coordinate &);
};
