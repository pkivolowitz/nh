// Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

#pragma once
#include <ctime>
#include <string>
#include <sys/time.h>

class GameTime {
public:
	GameTime();
	std::string GetCurrentTime();
};
