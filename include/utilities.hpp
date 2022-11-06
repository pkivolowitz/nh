#pragma once
#include <cstdlib>
#include <cinttypes>

inline int32_t RangeRand(int32_t min = 0, int32_t max = RAND_MAX) {
	return (rand() % (max - min)) + min;
}