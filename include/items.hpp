#pragma once
#include <string>
#include <cinttypes>

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
	std::string item_name;
	inline int32_t Weight() {
		return weight_per_item * number_of_like_items;
	}
};
