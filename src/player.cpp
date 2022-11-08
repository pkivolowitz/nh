#include <cassert>
#include "utilities.hpp"
#include "player.hpp"
#include <ncurses.h>

using namespace std;

void Player::Initialize() {
}

void Player::Display() {
	mvaddch(BOARD_TOP_OFFSET + pos.r, pos.c, '@');
}