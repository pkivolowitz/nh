// Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

#include <fstream>
#include <iostream>
#include <cstdlib>
#include <nlohmann/json.hpp>
#include "config.hpp"

using namespace std;
using json = nlohmann::json;

// Resolve ~/.pnhrc to an absolute path.
static string ConfigPath() {
	const char * home = getenv("HOME");
	if (!home) return ".pnhrc";
	return string(home) + "/.pnhrc";
}

bool GameConfig::Load() {
	string path = ConfigPath();
	ifstream in(path);
	if (!in.is_open()) {
		// No config file — write a default template for the player.
		WriteDefault();
		return false;
	}

	json j;
	try {
		in >> j;
	} catch (json::parse_error & e) {
		cerr << "Warning: " << path << ": " << e.what() << "\n";
		cerr << "Using defaults.\n";
		return false;
	}

	if (j.contains("name") && j["name"].is_string())
		name = j["name"].get<string>();
	if (j.contains("role") && j["role"].is_string())
		role = j["role"].get<string>();
	if (j.contains("race") && j["race"].is_string())
		race = j["race"].get<string>();
	if (j.contains("alignment") && j["alignment"].is_string())
		alignment = j["alignment"].get<string>();

	Validate();
	return true;
}

void GameConfig::Validate() {
	// Check role.
	if (!FindRole(role)) {
		cerr << "Warning: unknown role \"" << role
			 << "\", defaulting to Caveman.\n";
		role = "Caveman";
	}

	// Check race.
	if (!FindRace(race)) {
		cerr << "Warning: unknown race \"" << race
			 << "\", defaulting to Human.\n";
		race = "Human";
	}

	// Check alignment string.
	if (!IsValidAlignment(alignment)) {
		cerr << "Warning: unknown alignment \"" << alignment
			 << "\", defaulting to Neutral.\n";
		alignment = "Neutral";
	}

	// Check the full combination.
	if (!IsValidCombination(role, race, alignment)) {
		cerr << "Warning: " << race << " " << role
			 << " (" << alignment << ") is not a valid combination.\n";

		// Try to salvage: keep role, reset race to Human,
		// pick the first valid alignment for that combo.
		race = "Human";
		const RoleDef * rd = FindRole(role);
		if (rd && !rd->allowed_alignments.empty()) {
			alignment = AlignmentToString(rd->allowed_alignments[0]);
		} else {
			alignment = "Neutral";
		}
		cerr << "Falling back to Human " << role
			 << " (" << alignment << ").\n";
	}
}

bool GameConfig::WriteDefault() const {
	string path = ConfigPath();
	ofstream out(path);
	if (!out.is_open()) return false;

	json j;
	j["name"]      = "Unknown Player";
	j["role"]       = "Caveman";
	j["race"]       = "Human";
	j["alignment"]  = "Neutral";

	out << j.dump(4) << "\n";
	return true;
}
