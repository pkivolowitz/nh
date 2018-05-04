#pragma once
#include <vector>
#include "presentation.hpp"
#include "level.hpp"

class Game {
	public:
		Game();
		~Game();

		bool Initialize(Presentation * p, std::string & error);
		void Run(std::string & error);
		void End();
		
	private:
		void AddLevel();
		void EventLoop();
		bool HandleQuit();
		Presentation * p;
		std::vector<Level *> levels;
};
