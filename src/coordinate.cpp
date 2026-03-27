// Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

#include <iostream>
#include <iomanip>
#include <sstream>
#include "coordinate.hpp"

using namespace std;

// Format the coordinate as "(row,column)" for debugging output.
string Coordinate::to_string() {
	stringstream ss;
	ss << "(" << r << "," << c << ")";
	return ss.str();
}

// Provide strict weak ordering so coordinates can be map keys.
bool operator<(const Coordinate &l, const Coordinate &r) {
	return (l.r < r.r || (l.r == r.r && l.c < r.c));
}
