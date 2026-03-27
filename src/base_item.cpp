// Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

#include "items.hpp"

BaseItem::BaseItem() {
	type = BASE_ITEM;
	weight_per_item = 0;
	number_of_like_items = 1;	// An item exists as at least one instance.
	symbol = '?';
	item_name = "Generic Proxy Item";
}

BaseItem::~BaseItem() {
}

bool BaseItem::CanStackWith(const BaseItem & /*other*/) const {
	return false;
}
