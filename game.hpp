#pragma once
#include <vector>
#include <unistd.h>
#include "presentation.hpp"
#include "level.hpp"
#include "game_time.hpp"

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
		bool UpdateClock();
		void Delay(useconds_t d = 32 * 1000);

		bool HandleQuit();
		void HandleVersion();

		Presentation * p;
		int current_level;
		std::vector<Level *> levels;
		GameTime gt;
};
