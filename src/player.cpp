#include <ncurses.h>
#include <cassert>
#include <sstream>
#include <iomanip>
#include "utilities.hpp"
#include "player.hpp"
#include "colors.hpp"

using namespace std;

Player::Player() {
	for (int32_t index = 0; index < TRAIT_COUNT; index++) {
		current_traits[EXPERIENCE] = maximum_traits[EXPERIENCE] = 0;
		current_traits[LEVEL] = maximum_traits[LEVEL] = 1;
		current_traits[CONCENTRATION] = maximum_traits[CONCENTRATION] = RR(12,18);
		current_traits[HEALTH] = maximum_traits[HEALTH] = RR(12, 18);
		current_traits[INTELLIGENCE] = maximum_traits[INTELLIGENCE] = RR(12, 18);
		current_traits[DEXTERITY] = maximum_traits[DEXTERITY] = RR(12, 18);
	}
}

Player::~Player() {
	while (!inventory.empty()) {
		BaseItem * item = inventory.back();
		inventory.pop_back();
		delete item;
	}
}

void Player::Initialize() {
}

void Player::Display() {
	attron(COLOR_PAIR(CLR_PLAYER));
	attron(A_BOLD);
	mvaddch(BOARD_TOP_OFFSET + pos.r, pos.c, '@');
	attroff(A_BOLD);
	attroff(COLOR_PAIR(CLR_PLAYER));
}

void Player::AddToInventory(BaseItem * item) {
	assert(item);
	inventory.push_back(item);
}

int32_t Player::WeightOfInventory() {
	int32_t total_weight = 0;
	for (auto & itemptr : inventory) {
		total_weight += itemptr->Weight();
	}
	return total_weight;
}

int32_t Player::TotalInventoryCount() {
	int32_t total_items = 0;
	for (auto & itemptr : inventory) {
		total_items += itemptr->number_of_like_items;
	}
	return total_items;
}

string Player::to_string_2() {
	stringstream ss;
	ss << name << " ";
	ss << "HLTH: " << current_traits[HEALTH] << "/" << maximum_traits[HEALTH] << " ";
	ss << "CNC: " << current_traits[CONCENTRATION] << "/" << maximum_traits[CONCENTRATION] << " ";
	ss << "LVL: " << current_traits[LEVEL] << "/" << maximum_traits[LEVEL] << " ";
	ss << "EXP: " << current_traits[EXPERIENCE] << "/" << maximum_traits[EXPERIENCE] << " ";
	return ss.str();
}

string Player::to_string_1() {
	stringstream ss;
	ss << right << setw(name.size() + 6) << "INT: " << current_traits[INTELLIGENCE] << "/" << maximum_traits[INTELLIGENCE] << " ";
	ss << "CON: " << current_traits[CONSTITUTION] << "/" << maximum_traits[CONSTITUTION] << " ";
	ss << "INV: " << InventoryCount() << "/" << TotalInventoryCount() << "/";
	ss << WeightOfInventory();
	return ss.str();
}
