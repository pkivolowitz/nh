#include <cassert>
#include "floor_manager.hpp"
#include "logging.hpp"

using namespace std;

FloorManager::FloorManager() {
}

FloorManager::~FloorManager() {
	lock_guard<mutex> lg(lock);
	while (!items.empty()) {
		ItemPtr p = items.back();
		delete p;
		items.pop_back();
	}
}

char FloorManager::Top() {
	char retval = ' ';
	lock_guard<mutex> lg(lock);
	if (!items.empty()) {
		assert(items.front() != nullptr);
		retval = items.front()->Symbol();
	}
	return retval;
}

void FloorManager::Push(ItemPtr p) {
	assert(p != nullptr);
	lock_guard<mutex> lg(lock);
	items.push_back(p);
}

ItemPtr FloorManager::Pop() {
	ItemPtr retval = nullptr;
	lock_guard<mutex> lg(lock);
	if (!items.empty()) {
		retval = items.front();
		items.pop_back();
	}
	return retval;
}
