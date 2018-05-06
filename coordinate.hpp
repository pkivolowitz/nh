#pragma once

class Coordinate {
	public:
		Coordinate() { l = c = 0; }
		Coordinate(int l, int c) { this->l = l; this->c = c; }
		int l, c;

		Coordinate operator+(const Coordinate & rhs) { return Coordinate(this->l + rhs.l, this->c + rhs.c); }
		void Clip(int L, int C) { if (l >= L) l = L - 1; if (c >= C) c = C - 1; }
};
