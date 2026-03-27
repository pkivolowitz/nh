// Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

#pragma once
#include <string>
#include <vector>
#include <cinttypes>

// The three alignments from NetHack 3.6. Alignment affects
// artifact eligibility, prayer outcomes, and divine favor.
enum class Alignment { LAWFUL, NEUTRAL, CHAOTIC };

std::string AlignmentToString(Alignment a);
Alignment StringToAlignment(const std::string & s);
bool IsValidAlignment(const std::string & s);

// Role definition: the 13 NetHack 3.6 character classes.
// The allowed_races and allowed_alignments constrain character
// creation — the player's actual alignment is the intersection
// of role and race allowed alignments.
struct RoleDef {
	std::string name;
	std::vector<std::string> allowed_races;
	std::vector<Alignment> allowed_alignments;
};

// Race definition: the 5 NetHack 3.6 playable races.
struct RaceDef {
	std::string name;
	std::vector<Alignment> allowed_alignments;
};

// Lookup by name (case-insensitive). Returns nullptr if not found.
const RoleDef * FindRole(const std::string & name);
const RaceDef * FindRace(const std::string & name);

// Validate that a role/race/alignment combination is legal.
bool IsValidCombination(const std::string & role,
						const std::string & race,
						const std::string & alignment);

// Access the full tables for enumeration (e.g., character creation menus).
const std::vector<RoleDef> & GetAllRoles();
const std::vector<RaceDef> & GetAllRaces();
