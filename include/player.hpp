#pragma once
#include <string>
#include <vector>
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
	virtual ~Player();
	void Initialize();
	void Display();

	int32_t current_traits[TRAIT_COUNT];
	int32_t maximum_traits[TRAIT_COUNT];

	std::vector<BaseItem *> inventory;
	std::string to_string_1();
	std::string to_string_2();
	std::string name;

	void AddToInventory(BaseItem *);
	int32_t WeightOfInventory();
	int32_t TotalInventoryCount();
	inline size_t InventoryCount() {
		return inventory.size();
	}

	Coordinate pos;
};
