// Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

#pragma once
#include <vector>
#include "utilities.hpp"
#include "coordinate.hpp"

struct Room {
	// Randomize the room bounds and derived metadata.
	void Initialize(int32_t rn);
	// Return the cached center point of the room.
	Coordinate GetCentroid();

	Coordinate tl;
	Coordinate br;
	int32_t room_number;
	bool has_been_mapped;

private:
	Coordinate centroid;
};

using RoomVec = std::vector<Room>;
