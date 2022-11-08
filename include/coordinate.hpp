#pragma once
#include <cinttypes>
#include <string>

struct Coordinate {
	Coordinate() {
		c = r = 0;
	}

	Coordinate(const Coordinate & other) {
		c = other.c;
		r = other.r;
	}

	inline bool operator==(const Coordinate & other) {
		return c == other.c and r == other.r;
	}

	inline bool operator!=(const Coordinate & other) {
		return c != other.c or r != other.r;
	}

	std::string to_string();

	int32_t c, r;
};
