// Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

#include <ncurses.h>
#include <cassert>
#include <cstdio>
#include <sstream>
#include <iomanip>
#include "utilities.hpp"
#include "player.hpp"
#include "colors.hpp"

using namespace std;

// Roll the player's starting stats and baseline progression values.
Player::Player() {
	// Roll each stat-based trait independently.
	current_traits[INTELLIGENCE] = maximum_traits[INTELLIGENCE] = RR(12, 18);
	current_traits[CONSTITUTION] = maximum_traits[CONSTITUTION] = RR(12, 18);
	current_traits[DEXTERITY] = maximum_traits[DEXTERITY] = RR(12, 18);
	current_traits[HEALTH] = maximum_traits[HEALTH] = RR(12, 18);
	current_traits[CONCENTRATION] = maximum_traits[CONCENTRATION] = RR(12, 18);
	// Fixed starting values.
	current_traits[LEVEL] = maximum_traits[LEVEL] = 1;
	current_traits[EXPERIENCE] = maximum_traits[EXPERIENCE] = 0;
}

// Defaulted because inventory ownership is handled by unique_ptr.
Player::~Player() {
	// unique_ptr handles cleanup automatically.
}

// Placeholder hook for future post-construction setup.
void Player::Initialize() {
}

// Draw the player avatar at the current position.
void Player::Display(WINDOW * win) {
	wattron(win, COLOR_PAIR(CLR_PLAYER));
	wattron(win, A_BOLD);
	mvwaddch(win, BOARD_TOP_OFFSET + pos.r, pos.c, '@');
	wattroff(win, A_BOLD);
	wattroff(win, COLOR_PAIR(CLR_PLAYER));
}

// Find the first open inventory slot and return its letter.
char Player::NextAvailableLetter() const {
	for (int32_t i = 0; i < MAX_INVENTORY_SLOTS; i++) {
		if (!inventory[i]) {
			return IndexToLetter(i);
		}
	}
	return 0;
}

// Move an item into the next free inventory slot.
char Player::AddToInventory(unique_ptr<BaseItem> & item) {
	char letter = NextAvailableLetter();
	if (letter == 0) return 0;

	int32_t idx = LetterToIndex(letter);
	assert(idx >= 0 && idx < MAX_INVENTORY_SLOTS);
	inventory[idx] = std::move(item);
	return letter;
}

// Remove and return the item stored in the named inventory slot.
unique_ptr<BaseItem> Player::RemoveFromInventory(char letter) {
	int32_t idx = LetterToIndex(letter);
	if (idx < 0 || idx >= MAX_INVENTORY_SLOTS) return nullptr;
	return std::move(inventory[idx]);
}

// Sum the weight of all carried items.
int32_t Player::WeightOfInventory() const {
	int32_t total_weight = 0;
	for (auto & item : inventory) {
		if (item) {
			total_weight += item->Weight();
		}
	}
	return total_weight;
}

// Count the total number of item instances carried, including stacks.
int32_t Player::TotalInventoryCount() const {
	int32_t total_items = 0;
	for (auto & item : inventory) {
		if (item) {
			total_items += item->number_of_like_items;
		}
	}
	return total_items;
}

// Count the number of occupied inventory slots.
size_t Player::InventoryCount() const {
	size_t count = 0;
	for (auto & item : inventory) {
		if (item) count++;
	}
	return count;
}

// Render the inventory panel and its summary information.
void Player::RenderSidebar(WINDOW * win, bool detail_mode) const {
	int32_t max_rows, max_cols;
	getmaxyx(win, max_rows, max_cols);

	// Header
	wattron(win, A_BOLD);
	if (detail_mode) {
		mvwaddstr(win, 0, 1, "Inventory [detail]");
	} else {
		mvwaddstr(win, 0, 1, "Inventory");
	}
	wattroff(win, A_BOLD);

	// Item list — skip row 1 as a visual spacer.
	int32_t row = 2;
	for (int32_t i = 0; i < MAX_INVENTORY_SLOTS && row < max_rows - 4; i++) {
		if (!inventory[i]) continue;

		char letter = IndexToLetter(i);
		const auto & item = inventory[i];

		// Render the item symbol in its color before the letter line.
		int32_t sym = item->symbol;
		if (sym == '+') {
			wattron(win, COLOR_PAIR(CLR_SPELLBOOKS));
		}

		// "a - Unknown Spellbook"
		stringstream ss;
		ss << letter << " - " << item->item_name;
		string line = ss.str();
		if ((int32_t)line.size() > max_cols - 2) {
			line = line.substr(0, max_cols - 2);
		}
		mvwaddstr(win, row, 1, line.c_str());

		if (sym == '+') {
			wattroff(win, COLOR_PAIR(CLR_SPELLBOOKS));
		}
		row++;

		if (detail_mode && row < max_rows - 4) {
			// Indented detail line: weight and item type.
			stringstream ds;
			ds << "    Wt:" << item->Weight();
			switch (item->type) {
				case SPELLBOOK: ds << "  Spellbook"; break;
				case POTION:    ds << "  Potion";    break;
				case SCROLL:    ds << "  Scroll";    break;
				default:        break;
			}
			string detail = ds.str();
			if ((int32_t)detail.size() > max_cols - 2) {
				detail = detail.substr(0, max_cols - 2);
			}
			mvwaddstr(win, row, 1, detail.c_str());
			row++;
		}
	}

	// Summary block at the bottom of the sidebar.
	stringstream ws;
	ws << "Wt:" << WeightOfInventory();
	mvwaddstr(win, max_rows - 3, 1, ws.str().c_str());

	stringstream is;
	is << "Items:" << InventoryCount() << "/" << MAX_INVENTORY_SLOTS;
	mvwaddstr(win, max_rows - 2, 1, is.str().c_str());
}

// Format a stat as "LABEL:CUR/MAX" with right-justified numbers
// of the given width so values don't shift as they change.
static string FormatStat(const char * label, int32_t cur, int32_t max, int w) {
	char buf[32];
	snprintf(buf, sizeof(buf), "%s:%*d/%*d", label, w, cur, w, max);
	return buf;
}

// Build the status line containing name, role, and volatile stats.
string Player::to_string_2() {
	// "Name the Role" left-justified, then fixed-width stat blocks.
	// Title format matches NetHack: "Perry the Caveman"
	string title = name + " the " + role;
	char buf[128];
	snprintf(buf, sizeof(buf), "%-20s %s  %s  %s  %s",
		title.c_str(),
		FormatStat("HLTH", current_traits[HEALTH],
			maximum_traits[HEALTH], 3).c_str(),
		FormatStat("CNC", current_traits[CONCENTRATION],
			maximum_traits[CONCENTRATION], 3).c_str(),
		FormatStat("LVL", current_traits[LEVEL],
			maximum_traits[LEVEL], 2).c_str(),
		FormatStat("EXP", current_traits[EXPERIENCE],
			maximum_traits[EXPERIENCE], 6).c_str());
	return buf;
}

// Build the status line containing ancestry and inventory summary.
string Player::to_string_1() {
	// Race and alignment, then stat blocks aligned under line 1.
	string desc = race + " " + alignment;
	char buf[128];
	snprintf(buf, sizeof(buf), "%-20s %s  %s  %s  Items:%2d/%d Wt:%d",
		desc.c_str(),
		FormatStat("INT", current_traits[INTELLIGENCE],
			maximum_traits[INTELLIGENCE], 3).c_str(),
		FormatStat("CON", current_traits[CONSTITUTION],
			maximum_traits[CONSTITUTION], 3).c_str(),
		FormatStat("DEX", current_traits[DEXTERITY],
			maximum_traits[DEXTERITY], 3).c_str(),
		(int)InventoryCount(), MAX_INVENTORY_SLOTS,
		WeightOfInventory());
	return buf;
}
