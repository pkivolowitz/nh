#pragma once
#include <string>

class Coordinate {
	public:
		Coordinate();
		Coordinate(int l, int c);

		int l, c;

		Coordinate operator+(const Coordinate & rhs);
		static Coordinate Centroid(const Coordinate & a, const Coordinate & b);
		void Clip(int L, int C);
		std::string to_string();
};
