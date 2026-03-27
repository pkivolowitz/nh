// Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

#pragma once
#include <cinttypes>
#include <string>
#include <cmath>

struct Coordinate {
	// Initialize the coordinate at the origin.
	Coordinate() {
		c = r = 0;
	}

	// Initialize the coordinate with explicit row and column values.
	Coordinate(int32_t r, int32_t c) {
		this->r = r;
		this->c = c;
	}
	
	// Copy another coordinate.
	Coordinate(const Coordinate & other) {
		c = other.c;
		r = other.r;
	}

	// Compute Euclidean distance to another coordinate.
	inline double Distance(Coordinate & other) {
		double dr = r - other.r;
		double dc = c - other.c;
		return sqrt(dr * dr + dc * dc);
	}

	// Subtract another coordinate component-wise.
	inline Coordinate operator-(const Coordinate & other) {
		Coordinate retval(r - other.r, c - other.c);
		return retval;
	}

	// Add another coordinate component-wise.
	inline Coordinate operator+(const Coordinate &other) {
		Coordinate retval(r + other.r, c + other.c);
		return retval;
	}

	// Scale the coordinate by a scalar factor.
	inline Coordinate operator*(const double t) {
		Coordinate retval(int32_t(r * t), int32_t(c * t));
		return retval;
	}

	// Linearly interpolate from this coordinate toward another.
	inline Coordinate LERP(const Coordinate &other, double t) {
		Coordinate retval = Coordinate(other.r - r, other.c - c);
		retval = retval * t + *this;
		return retval;
	}

	// Compare coordinates for exact equality.
	inline bool operator==(const Coordinate &other) {
		return c == other.c and r == other.r;
	}

	// Compare coordinates for inequality.
	inline bool operator!=(const Coordinate & other) {
		return c != other.c or r != other.r;
	}

	// Format the coordinate for logs and diagnostics.
	std::string to_string();

	int32_t c, r;
};
