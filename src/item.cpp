#include "item.hpp"
#include "logging.hpp"

Item::Item() {
	symbol = ' ';
}

chtype Item::Symbol() {
	return symbol;
}
