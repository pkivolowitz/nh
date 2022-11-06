#include <sstream>
#include <iomanip>
#include "player.hpp"
#include "utilities.hpp"

using namespace std;

Player::Player() {
	health.SetBoth(RangeRand(12, 18));
	power.SetBoth(RangeRand(12, 18));
	experience.SetBoth(0);
	strength.SetBoth(RangeRand(12, 18));
	dexterity.SetBoth(RangeRand(12, 18));
	constitution.SetBoth(RangeRand(12, 18));
	intelligence.SetBoth(RangeRand(12, 18));
	charisma.SetBoth(RangeRand(12, 18));
	gold = 0;
	player_level = 1;
	name = "Horse";
}

string Player::to_string() {
	stringstream ss;
	ss << setw(20) << left << name;
	ss << "st: " << setw(4) << strength.current;
	ss << "dx: " << setw(4) << dexterity.current;
	ss << "in: " << setw(4) << intelligence.current;
	ss << "co: " << setw(4) << constitution.current;
	ss << "ch: " << setw(4) << charisma.current;
	return ss.str();
}