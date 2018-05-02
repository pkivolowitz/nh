#pragma once
#include <vector>
#include "presentation.hpp"
#include "level.hpp"

class Game {
	public:
		Game();
		~Game();

		bool Initialize(Presentation * p, std::string & error);
		void AddLevel();
		void End();
		
	private:
		Presentation * p;
		std::vector<Level *> levels;
};
