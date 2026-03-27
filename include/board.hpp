// Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

#pragma once
#include <cinttypes>
#include <vector>
#include <string>
#include <memory>
#include <assert.h>
#include <ncurses.h>
#include "utilities.hpp"
#include "cell.hpp"
#include "room.hpp"
#include "player.hpp"
#include "game_time.hpp"
#include "items.hpp"

using ivec = std::vector<int32_t>;

struct Board {
	Board();

	// The ncurses window this board renders into. Set by the
	// caller after construction — all boards share one window
	// since only one is displayed at a time.
	WINDOW * win = nullptr;

	Cell cells[BOARD_ROWS][BOARD_COLUMNS];
	void Display(Player & p, bool show_original, double tr = 2.5);
	void ClearInfoLine();
	void ReportGoodies(Coordinate & c);
	int32_t GetGoodieCount(Coordinate & c);
	bool IsDownstairs(Coordinate & c);
	bool IsUpstairs(Coordinate & c);
	bool IsAStairway(Coordinate &);
	bool IsNavigable(Coordinate &);
	void UpdateTime();

	// Add item to the floor at the given coordinate.
	void AddGoodie(Coordinate c, std::unique_ptr<BaseItem> item);

	// Door interaction. Returns a message string for the info line.
	std::string TryOpenDoor(Coordinate & c);
	std::string TryCloseDoor(Coordinate & c);
	bool IsDoor(Coordinate & c);
	bool IsDoorPassable(Coordinate & c);

	// Remove and return all items at the given coordinate.
	// Returns an empty vector if nothing is there.
	std::vector<std::unique_ptr<BaseItem>> RemoveGoodies(Coordinate c);

	Coordinate upstairs;
	Coordinate downstairs;

	void DebugPrintBoard(int32_t mode);
	int32_t GetSymbol(Coordinate);

	GoodieMap goodies;
	RoomVec rooms;

	static const int32_t MIN_ROOMS = 6;
	static const int32_t MAX_ROOMS = 9;

private:
	std::string BuildCornerKey(Coordinate & c);
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
	bool PlanBForCooridors(uint32_t room_index);
	void FlattenRooms();
	void LayCorridor(Coordinate &, Coordinate &);
	void Show(bool show_original, Coordinate & coord, const Cell & cell);
	bool LineOfSight(Coordinate & player, Coordinate & cell);
	void PlaceDoors();
	void UpdateDoorDisplay(int32_t r, int32_t c);
	void PlaceGoodies();
	void PrintGoodies();

	inline bool IsCorridor(Coordinate c) {
		return IsCorridor(c.r, c.c);
	}

	inline bool IsCorridor(int32_t r, int32_t c) {
		assert(r >= 0 and r < BOARD_ROWS);
		assert(c >= 0 and c < BOARD_COLUMNS);
		return cells[r][c].base_type == CORRIDOR;
	}

	inline bool IsEmpty(Coordinate & c) {
		return cells[c.r][c.c].base_type == EMPTY;
	}

	inline bool IsNeighbor(Coordinate & a, Coordinate & b) {
		return abs(a.r - b.r) <= 1 and abs(a.c - b.c) <= 1;
	}

	void MakeCorridor(Coordinate &c);
	void MakeCorridor(Cell &c);
};
