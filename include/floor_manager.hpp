#pragma once
#include <vector>
#include "curses.h"
#include "item.hpp"

class FloorManager {
	public:
		FloorManager();
		~FloorManager();

		chtype Top();
		void Push(ItemPtr);
		ItemPtr Pop();
		const ItemPtr  Peek();

	private:
		std::vector<ItemPtr> items;
};

