// Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

#pragma once
#include <string>
#include "game_defs.hpp"

// Game configuration loaded from ~/.pnhrc (JSON).
// Missing or invalid fields fall back to defaults.
// An invalid role/race/alignment combination is rejected
// with a diagnostic to stderr.
struct GameConfig {
	std::string name       = "Unknown Player";
	std::string role       = "Caveman";
	std::string race       = "Human";
	std::string alignment  = "Neutral";

	// Load from ~/.pnhrc. Returns true if file was found and
	// parsed (even if some fields fell back to defaults).
	// Returns false if the file doesn't exist (not an error).
	bool Load();

	// Write a default config file to ~/.pnhrc. Used when none
	// exists so the player has a template to edit.
	bool WriteDefault() const;

private:
	// Validate and fix the loaded combination. Prints warnings
	// to stderr for invalid values and falls back to defaults.
	void Validate();
};
