#include <cassert>
#include "floor_manager.hpp"
#include "level.hpp"
#include "logging.hpp"

using namespace std;

FloorManager::FloorManager() {
}

FloorManager::~FloorManager() {
	while (!items.empty()) {
		ItemPtr p = items.back();
		delete p;
		items.pop_back();
	}
}

char FloorManager::Top() {
	char retval = '\0';
	if (!items.empty()) {
		assert(items.front() != nullptr);
		retval = items.front()->Symbol();
	}
	return retval;
}

void FloorManager::Push(ItemPtr p) {
	assert(p != nullptr);
	items.push_back(p);
}

ItemPtr FloorManager::Pop() {
	ItemPtr retval = nullptr;
	if (!items.empty()) {
		retval = items.front();
		items.pop_back();
	}
	return retval;
}

const ItemPtr FloorManager::Peek() {
	ItemPtr retval = nullptr;
	if (!items.empty()) {
		retval = items.front();
	}
	return retval;
}
	
