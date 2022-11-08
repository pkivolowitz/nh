#pragma once
#include <string>
#include <vector>
#include "room.hpp"
#include "coordinate.hpp"

struct Player {
	void Initialize();
	void Display();
	Coordinate pos;
};
