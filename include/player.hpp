#pragma once
#include <cinttypes>
#include <vector>
#include <string>
#include "item.hpp"

struct Stat {
	int32_t current;
	int32_t maximum;

	inline void SetBoth(int32_t v) {
		current = maximum = v;
	}
};

class Player {
public:
	Player();
	std::string to_string();

private:
	std::string name;
	Stat health;
	Stat power;
	Stat experience;
	Stat strength;
	Stat dexterity;
	Stat constitution;
	Stat intelligence;
	Stat charisma;

	int32_t player_level;
	int32_t gold;
	std::vector<Item> inventory;
};
