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
	// Build and populate a new dungeon level.
	Board();

	// The ncurses window this board renders into. Set by the
	// caller after construction — all boards share one window
	// since only one is displayed at a time.
	WINDOW * win = nullptr;

	Cell cells[BOARD_ROWS][BOARD_COLUMNS];
	// Render the board into the window using the player's position as context.
	void Display(Player & p, bool show_original, double tr = 2.5);
	// Clear the informational message line at the top of the map.
	void ClearInfoLine();
	// Describe items lying on the given coordinate.
	void ReportGoodies(Coordinate & c);
	// Return the number of items lying on the given coordinate.
	int32_t GetGoodieCount(Coordinate & c);
	// Report whether the coordinate holds the down staircase.
	bool IsDownstairs(Coordinate & c);
	// Report whether the coordinate holds the up staircase.
	bool IsUpstairs(Coordinate & c);
	// Report whether the coordinate holds either staircase.
	bool IsAStairway(Coordinate &);
	// Report whether the player can currently move onto the coordinate.
	bool IsNavigable(Coordinate &);
	// Refresh the clock shown in the map window.
	void UpdateTime();

	// Add item to the floor at the given coordinate.
	void AddGoodie(Coordinate c, std::unique_ptr<BaseItem> item);

	// Door interaction. Returns a message string for the info line.
	// Attempt to open the door at the given coordinate.
	std::string TryOpenDoor(Coordinate & c);
	// Attempt to close the door at the given coordinate.
	std::string TryCloseDoor(Coordinate & c);
	// Report whether the coordinate contains a door cell.
	bool IsDoor(Coordinate & c);
	// Report whether the door at the coordinate allows passage.
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
	// Build the 3x3 neighborhood key used to choose line-drawing glyphs.
	std::string BuildCornerKey(Coordinate & c);
	// Build the 3x3 neighborhood key used to choose line-drawing glyphs.
	std::string BuildCornerKey(int32_t r, int32_t c);
	// Reset board state before generating a new level.
	void Clear();
	// Generate the rooms, corridors, doors, stairs, and floor items.
	void Create();
	// Collect rows where corridors should be avoided to preserve wall outlines.
	void FindRowsToAvoid(ivec &r_avoid);
	// Collect columns where corridors should be avoided to preserve wall outlines.
	void FindColsToAvoid(ivec &c_avoid);
	// Choose a corridor endpoint inside a room that avoids ugly wall-hugging paths.
	void FindGCoords(ivec &br, ivec &bc, Room &r, Coordinate &coord);
	// Fill the room interior with temporary room markers.
	void Fill(int32_t rn);
	// Add wall cells around the room's perimeter.
	void Enclose(int32_t rn);
	// Convert raw wall markers into their final line-drawing glyphs.
	void PlaceCorners();
	// Connect generated rooms with corridors.
	void PlaceCorridors();
	// Choose staircase positions for the level.
	void PlaceStairs();
	// Placeholder for corridor post-processing that adds bends and branches.
	void MakeKinks();
	// Pick a non-stair floor tile inside a room for stair placement.
	Coordinate GetGoodStairLocation(Room & room);
	// Fallback corridor generation when the primary planner fails for a room.
	bool PlanBForCooridors(uint32_t room_index);
	// Merge overlapping room regions into single flattened room ids.
	void FlattenRooms();
	// Carve a corridor path between two chosen endpoints.
	void LayCorridor(Coordinate &, Coordinate &);
	// Draw a single visible cell with any needed item or color overrides.
	void Show(bool show_original, Coordinate & coord, const Cell & cell);
	// Determine whether one coordinate can see another.
	bool LineOfSight(Coordinate & player, Coordinate & cell);
	// Convert corridor-wall transition points into actual doors.
	void PlaceDoors();
	// Update the displayed glyph for a door after its state changes.
	void UpdateDoorDisplay(int32_t r, int32_t c);
	// Seed each room with starting floor items.
	void PlaceGoodies();
	// Dump item placement to the debug log.
	void PrintGoodies();

	// Forward to the row/column overload for corridor tests.
	inline bool IsCorridor(Coordinate c) {
		return IsCorridor(c.r, c.c);
	}

	// Report whether the given board cell is a corridor.
	inline bool IsCorridor(int32_t r, int32_t c) {
		assert(r >= 0 and r < BOARD_ROWS);
		assert(c >= 0 and c < BOARD_COLUMNS);
		return cells[r][c].base_type == CORRIDOR;
	}

	// Report whether the coordinate is still empty / ungenerated.
	inline bool IsEmpty(Coordinate & c) {
		return cells[c.r][c.c].base_type == EMPTY;
	}

	// Report whether two coordinates touch orthogonally or diagonally.
	inline bool IsNeighbor(Coordinate & a, Coordinate & b) {
		return abs(a.r - b.r) <= 1 and abs(a.c - b.c) <= 1;
	}

	// Carve a corridor at the given coordinate.
	void MakeCorridor(Coordinate &c);
	// Convert a cell into corridor floor, preserving door-candidate metadata.
	void MakeCorridor(Cell &c);
};
