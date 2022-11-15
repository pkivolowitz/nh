#pragma once
#include <cinttypes>

enum Spells {
	SPELL_NONE,
	SPELL_FIRE
};

struct Spell {
	Spell();

	int32_t last_cast_on_turn;
};
