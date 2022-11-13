#pragma once
#include <cinttypes>
#include <string>
#include <cmath>

struct Coordinate {
	Coordinate() {
		c = r = 0;
	}

	Coordinate(int32_t r, int32_t c) {
		this->r = r;
		this->c = c;
	}
	
	Coordinate(const Coordinate & other) {
		c = other.c;
		r = other.r;
	}

	inline double Distance(Coordinate & other) {
		double dr = r - other.r;
		double dc = c - other.c;
		return sqrt(dr * dr + dc * dc);
	}

	inline Coordinate operator-(const Coordinate & other) {
		Coordinate retval(r - other.r, c - other.c);
		return retval;
	}

	inline Coordinate operator+(const Coordinate &other) {
		Coordinate retval(r + other.r, c + other.c);
		return retval;
	}

	inline Coordinate operator*(const double t) {
		Coordinate retval(int32_t(r * t), int32_t(c * t));
		return retval;
	}

	inline Coordinate LERP(const Coordinate &other, double t) {
		Coordinate retval = Coordinate(other.r - r, other.c - c);
		retval = retval * t + *this;
		return retval;
	}

	inline bool operator==(const Coordinate &other) {
		return c == other.c and r == other.r;
	}

	inline bool operator!=(const Coordinate & other) {
		return c != other.c or r != other.r;
	}

	std::string to_string();

	int32_t c, r;
};
