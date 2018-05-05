#pragma once
#include <vector>
#include <thread>
#include <mutex>
#include "item.hpp"

class FloorManager {
	public:
		FloorManager();
		~FloorManager();
		
		char Top();
		void Push(ItemPtr);
		ItemPtr Pop();

	private:
		std::vector<ItemPtr> items;
		std::mutex lock;
};

