#pragma once
#include <cinttypes>
#include <vector>
#include <string>
#include "utilities.hpp"
#include "cell.hpp"
#include "room.hpp"
#include "player.hpp"

using ivec = std::vector<int32_t>;

struct Board {
	Board();

	Cell cells[BOARD_ROWS][BOARD_COLUMNS];
	void Display(Player & p, bool show_original, double tr = 2.5);
	bool IsDownstairs(Coordinate & c);
	bool IsUpstairs(Coordinate & c);
	bool IsAStairway(Coordinate &);
	bool IsNavigable(Coordinate &);
	
	Coordinate upstairs;
	Coordinate downstairs;

	void DebugPrintBoard(int32_t mode);

	RoomVec rooms;

private:
	std::string BuildCornerKey(int32_t r, int32_t c);
	void Clear();
	void Create();
	void FindRowsToAvoid(ivec &r_avoid);
	void FindColsToAvoid(ivec &c_avoid);
	void FindGCoords(ivec &br, ivec &bc, Room &r, Coordinate &coord);
	void Fill(int32_t rn);
	void Enclose(int32_t rn);
	void PlaceCorners();
	void PlaceCorridors();
	void PlaceStairs();
	void MakeKinks();
	Coordinate GetGoodStairLocation(Room & room);
	//void RemoveFloorDigits();
	bool PlanBForCooridors(uint32_t room_index);
	void FlattenRooms();
	void LayCorridor(Coordinate &, Coordinate &);
	void Show(bool show_original, Coordinate & coord, const Cell & cell);
	bool LineOfSight(Coordinate & player, Coordinate & cell);
	
	inline bool IsCorridor(int32_t r, int32_t c) {
		assert(r >= 0 and r < BOARD_ROWS);
		assert(c >= 0 and c < BOARD_COLUMNS);
		return cells[r][c].base_type == CORRIDOR;	
	}
};
