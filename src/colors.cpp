// Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

#include <ncurses.h>
#include "colors.hpp"

void CursesColorSupport::Initialize() {
    start_color();
    use_default_colors();
    init_pair(CLR_EMPTY, COLOR_WHITE, -1);
    init_pair(CLR_PLAYER, COLOR_CYAN, -1);
	init_pair(CLR_SPELLBOOKS, COLOR_RED, -1);
	init_pair(CLR_DOORS, COLOR_YELLOW, -1);
}