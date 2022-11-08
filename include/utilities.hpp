#pragma once
#include <cstdlib>
#include <cinttypes>

/*	RR - produce random numbers between the min and max arguments,
	inclusive.
*/
static inline int32_t RR(int32_t min = 0, int32_t max = RAND_MAX) {
	return (rand() % (max - min + 1)) + min;
}

static const int32_t BOARD_COLUMNS = 80;
static const int32_t BOARD_ROWS = 20;
static const int32_t BOARD_TOP_OFFSET = 2;

extern int32_t seed;
extern int32_t screen_counter;
