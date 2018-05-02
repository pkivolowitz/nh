#pragma once
#include <vector>
#include "player.hpp"

class Level {
	public:
		Level();
		bool Initialize(int lines, int cols, std::vector<Player> & players);
};
