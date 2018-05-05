#pragma once
#include <ctime>
#include <string>
#include <sys/time.h>

class GameTime {
	public:
		GameTime();
		std::string GetCurrentTime();
};
