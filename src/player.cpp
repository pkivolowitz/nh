#include <ncurses.h>
#include <cassert>
#include "utilities.hpp"
#include "player.hpp"
#include "colors.hpp"

using namespace std;

void Player::Initialize() {
}

void Player::Display() {
	attron(COLOR_PAIR(CLR_PLAYER));
	attron(A_BOLD);
	mvaddch(BOARD_TOP_OFFSET + pos.r, pos.c, '@');
	attroff(A_BOLD);
	attroff(COLOR_PAIR(CLR_PLAYER));
}