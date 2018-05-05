#pragma once
#include <vector>
#include "item.hpp"

class FloorManager {
	public:
		FloorManager();
		~FloorManager();

		char Top();
		void Push(ItemPtr);
		ItemPtr Pop();
		const ItemPtr  Peek();

	private:
		std::vector<ItemPtr> items;
};

