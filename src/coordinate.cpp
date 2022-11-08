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