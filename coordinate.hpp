#pragma once

class Coordinate {
	public:
		Coordinate() { l = c = 0; }
		Coordinate(int l, int c) { this->l = l; this->c = c; }
		int l, c;

		Coordinate operator+(const Coordinate & rhs) { return Coordinate(this->l + rhs.l, this->c + rhs.c); }
		void Clip(int L, int C) { if (l >= L - 1) l = L - 2; if (c >= C - 1) c = C - 2; }
};
