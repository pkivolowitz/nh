#pragma once
#include <vector>
#include "utilities.hpp"
#include "coordinate.hpp"

struct Room {
	void Initialize(int32_t rn);
	Coordinate GetCentroid();

	Coordinate tl;
	Coordinate br;
	int32_t room_number;
	bool has_been_mapped;

private:
	Coordinate centroid;
};

using RoomVec = std::vector<Room>;
