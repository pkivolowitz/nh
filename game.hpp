#pragma once
#include <vector>
#include "presentation.hpp"
#include "level.hpp"

class Game {
	public:
		Game();
		bool Initialize(Presentation & p, std::string & error);

	private:
		std::vector<Level> levels;
};
