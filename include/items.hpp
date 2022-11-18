#pragma once
#include <string>
#include <cinttypes>
#include <vector>
#include <map>
#include "coordinate.hpp"

enum ItemType {
	BASE_ITEM,
	POTION,
	SCROLL,
	SPELLBOOK
};

struct BaseItem {
public:
	BaseItem();
	virtual ~BaseItem();

	ItemType type;
	int32_t weight_per_item;
	int32_t number_of_like_items;
	int32_t symbol;
	std::string item_name;
	inline int32_t Weight() {
		return weight_per_item * number_of_like_items;
	}
};

struct Spellbook : public BaseItem {
	Spellbook();
};

using GoodieMap = std::map<Coordinate, std::vector<BaseItem>>;
