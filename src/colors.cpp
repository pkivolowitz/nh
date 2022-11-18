#include <ncurses.h>
#include "colors.hpp"

void CursesColorSupport::Initialize() {
    start_color();
    use_default_colors();
    init_pair(CLR_EMPTY, COLOR_WHITE, -1);
    init_pair(CLR_PLAYER, COLOR_CYAN, -1);
	init_pair(CLR_SPELLBOOKS, COLOR_RED, -1);
}