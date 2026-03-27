// Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

#pragma once
#include <string>

// Parse supported command-line flags and update startup options.
bool HandleOptions(
	int argc, 
	char **argv, 
	std::string & player_name
);
