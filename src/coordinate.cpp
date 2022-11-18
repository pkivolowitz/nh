#include <iostream>
#include <iomanip>
#include <sstream>
#include "coordinate.hpp"

using namespace std;

string Coordinate::to_string() {
	stringstream ss;
	ss << "(" << r << "," << c << ")";
	return ss.str();
}

bool operator<(const Coordinate &l, const Coordinate &r) {
	return (l.r < r.r || (l.r == r.r && l.c < r.c));
}