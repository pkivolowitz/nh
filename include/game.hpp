#pragma once
#include <vector>
#include <unistd.h>
#include "presentation.hpp"
#include "level.hpp"
#include "game_time.hpp"
#include "player.hpp"

class Game {
	public:
		Game();
		~Game();

		void Initialize(Presentation * p);
		void Run();
		void End();
		
	private:
		void AddLevel();
		void EventLoop();
		bool UpdateClock();
		bool UpdatePlayer();
		void Delay(useconds_t d = 32 * 1000);

		bool HandleQuit();
		void HandleVersion();

		Presentation * p;
		int current_level;
		std::vector<Level *> levels;
		GameTime gt;
		Player player;
};
