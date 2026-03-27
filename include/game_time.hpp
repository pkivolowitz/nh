// Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

#pragma once
#include <ctime>
#include <string>
#include <sys/time.h>

class GameTime {
public:
	// Construct a helper object for producing wall-clock timestamps.
	GameTime();
	// Return the current local time formatted as HH:MM:SS.
	std::string GetCurrentTime();
};
