// Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

#include <algorithm>
#include "game_defs.hpp"

using namespace std;

// NetHack 3.6 roles: each role lists its allowed races and alignments.
// The player's actual alignment must be in the intersection of the
// role's and race's allowed alignment sets.
static vector<RoleDef> roles = {
	{"Archeologist", {"Human", "Dwarf", "Gnome"},          {Alignment::LAWFUL, Alignment::NEUTRAL}},
	{"Barbarian",    {"Human", "Orc"},                     {Alignment::NEUTRAL, Alignment::CHAOTIC}},
	{"Caveman",      {"Human", "Dwarf", "Gnome"},          {Alignment::LAWFUL, Alignment::NEUTRAL}},
	{"Healer",       {"Human", "Gnome"},                   {Alignment::NEUTRAL}},
	{"Knight",       {"Human"},                            {Alignment::LAWFUL}},
	{"Monk",         {"Human"},                            {Alignment::LAWFUL, Alignment::NEUTRAL, Alignment::CHAOTIC}},
	{"Priest",       {"Human", "Elf"},                     {Alignment::LAWFUL, Alignment::NEUTRAL, Alignment::CHAOTIC}},
	{"Ranger",       {"Human", "Elf", "Gnome", "Orc"},    {Alignment::NEUTRAL, Alignment::CHAOTIC}},
	{"Rogue",        {"Human", "Orc"},                     {Alignment::CHAOTIC}},
	{"Samurai",      {"Human"},                            {Alignment::LAWFUL}},
	{"Tourist",      {"Human"},                            {Alignment::NEUTRAL}},
	{"Valkyrie",     {"Human", "Dwarf"},                   {Alignment::LAWFUL, Alignment::NEUTRAL}},
	{"Wizard",       {"Human", "Elf", "Gnome", "Orc"},    {Alignment::NEUTRAL, Alignment::CHAOTIC}},
};

// NetHack 3.6 races with their allowed alignments.
static vector<RaceDef> races = {
	{"Human", {Alignment::LAWFUL, Alignment::NEUTRAL, Alignment::CHAOTIC}},
	{"Elf",   {Alignment::CHAOTIC}},
	{"Dwarf", {Alignment::LAWFUL}},
	{"Gnome", {Alignment::NEUTRAL}},
	{"Orc",   {Alignment::CHAOTIC}},
};

// Case-insensitive string comparison.
static bool StrEqCI(const string & a, const string & b) {
	if (a.size() != b.size()) return false;
	for (size_t i = 0; i < a.size(); i++) {
		if (tolower(a[i]) != tolower(b[i])) return false;
	}
	return true;
}

string AlignmentToString(Alignment a) {
	switch (a) {
		case Alignment::LAWFUL:  return "Lawful";
		case Alignment::NEUTRAL: return "Neutral";
		case Alignment::CHAOTIC: return "Chaotic";
	}
	return "Unknown";
}

Alignment StringToAlignment(const string & s) {
	if (StrEqCI(s, "Lawful"))  return Alignment::LAWFUL;
	if (StrEqCI(s, "Chaotic")) return Alignment::CHAOTIC;
	return Alignment::NEUTRAL;
}

bool IsValidAlignment(const string & s) {
	return StrEqCI(s, "Lawful") ||
		   StrEqCI(s, "Neutral") ||
		   StrEqCI(s, "Chaotic");
}

const RoleDef * FindRole(const string & name) {
	for (auto & r : roles) {
		if (StrEqCI(r.name, name)) return &r;
	}
	return nullptr;
}

const RaceDef * FindRace(const string & name) {
	for (auto & r : races) {
		if (StrEqCI(r.name, name)) return &r;
	}
	return nullptr;
}

// An alignment is valid for a role+race if it appears in BOTH
// the role's and race's allowed alignment lists.
bool IsValidCombination(const string & role_name,
						const string & race_name,
						const string & align_name)
{
	const RoleDef * role = FindRole(role_name);
	const RaceDef * race = FindRace(race_name);
	if (!role || !race) return false;

	// Race must be allowed for this role.
	bool race_ok = false;
	for (auto & rn : role->allowed_races) {
		if (StrEqCI(rn, race_name)) { race_ok = true; break; }
	}
	if (!race_ok) return false;

	if (!IsValidAlignment(align_name)) return false;
	Alignment a = StringToAlignment(align_name);

	// Alignment must be in both role's and race's lists.
	bool in_role = false, in_race = false;
	for (auto ra : role->allowed_alignments) {
		if (ra == a) { in_role = true; break; }
	}
	for (auto ra : race->allowed_alignments) {
		if (ra == a) { in_race = true; break; }
	}
	return in_role && in_race;
}

const vector<RoleDef> & GetAllRoles() { return roles; }
const vector<RaceDef> & GetAllRaces() { return races; }
