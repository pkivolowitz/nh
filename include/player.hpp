// Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

#pragma once
#include <string>
#include <memory>
#include <array>
#include <ncurses.h>
#include "room.hpp"
#include "coordinate.hpp"
#include "items.hpp"

enum Traits {
	INTELLIGENCE,
	CONSTITUTION,
	DEXTERITY,
	LEVEL,
	EXPERIENCE,
	HEALTH,
	CONCENTRATION,
	TRAIT_COUNT			// Must be last.
};

struct Player {
	Player();
	// Release any player-owned resources.
	virtual ~Player();
	// Populate any additional runtime state after construction.
	void Initialize();
	// Draw the player glyph on the map window.
	void Display(WINDOW * win);

	int32_t current_traits[TRAIT_COUNT];
	int32_t maximum_traits[TRAIT_COUNT];

	// Letter-indexed inventory: a-z = slots 0-25, A-Z = slots 26-51.
	// Each slot holds at most one item (or stack for stackable types).
	std::array<std::unique_ptr<BaseItem>, MAX_INVENTORY_SLOTS> inventory;

	// Add item to next available slot. Returns assigned letter,
	// or 0 if inventory is full. On failure the caller retains
	// ownership — the unique_ptr is NOT consumed.
	char AddToInventory(std::unique_ptr<BaseItem> & item);

	// Remove item from slot identified by letter. Returns the
	// item, or nullptr if the slot was empty or letter invalid.
	std::unique_ptr<BaseItem> RemoveFromInventory(char letter);

	// First empty inventory slot as a letter, or 0 if full.
	char NextAvailableLetter() const;

	// Return the total weight of every item in inventory.
	int32_t WeightOfInventory() const;
	// Return the sum of item counts across all occupied slots.
	int32_t TotalInventoryCount() const;
	// Return the number of occupied inventory slots.
	size_t InventoryCount() const;

	// Render the inventory sidebar into the given window.
	void RenderSidebar(WINDOW * win, bool detail_mode) const;

	// Build the lower status line string.
	std::string to_string_1();
	// Build the upper status line string.
	std::string to_string_2();

	std::string name;
	std::string role;
	std::string race;
	std::string alignment;

	Coordinate pos;
};
