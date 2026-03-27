// Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

#pragma once
#include <string>
#include <cinttypes>
#include <vector>
#include <map>
#include <memory>
#include "coordinate.hpp"

enum ItemType {
	BASE_ITEM,
	POTION,
	SCROLL,
	SPELLBOOK
};

// Maximum inventory slots: a-z (26) + A-Z (26) = 52.
static const int32_t MAX_INVENTORY_SLOTS = 52;

// Convert inventory letter to array index.
// a-z maps to 0-25, A-Z maps to 26-51, anything else returns -1.
inline int32_t LetterToIndex(char c) {
	if (c >= 'a' && c <= 'z') return c - 'a';
	if (c >= 'A' && c <= 'Z') return c - 'A' + 26;
	return -1;
}

// Convert array index back to the inventory letter.
// 0-25 maps to a-z, 26-51 maps to A-Z, out of range returns '?'.
inline char IndexToLetter(int32_t i) {
	if (i >= 0 && i < 26) return 'a' + i;
	if (i >= 26 && i < 52) return 'A' + (i - 26);
	return '?';
}

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

	// Whether this item can stack with another of the same type.
	// Default: no stacking. Override in subclasses for stackable
	// item types (e.g., identical potions or scrolls with same BUC).
	virtual bool CanStackWith(const BaseItem & other) const;
};

struct Spellbook : public BaseItem {
	Spellbook();
	// Spellbooks never stack — each contains a different spell.
	bool CanStackWith(const BaseItem & /*other*/) const override {
		return false;
	}
};

using GoodieMap = std::map<Coordinate, std::vector<std::unique_ptr<BaseItem>>>;
