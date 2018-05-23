#include "coordinate.hpp"
#include <sstream>

using namespace std;

Coordinate::Coordinate() { 
	l = c = 0; 
}

Coordinate::Coordinate(int l, int c) { 
	this->l = l; this->c = c; 
}

Coordinate Coordinate::operator+(const Coordinate & rhs) { 
	return Coordinate(this->l + rhs.l, this->c + rhs.c); 
}

Coordinate Coordinate::Centroid(const Coordinate & a, const Coordinate & b) {
	return Coordinate((a.l + b.l) / 2, (a.c + b.c) / 2);
}

void Coordinate::Clip(int L, int C) { if (l >= L - 1) l = L - 2; if (c >= C - 1) c = C - 2; }

string Coordinate::to_string() {
	stringstream ss;
	ss << "(" << l << ", " << c << ")";
	return ss.str();
}
