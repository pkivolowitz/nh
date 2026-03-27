// Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

#pragma once
#include <cinttypes>
#include <map>
#include <string>
#include <ncurses.h>

using CornerMap = std::map<std::string, int32_t>;

extern CornerMap corner_map;

void InitializeCornerMap();