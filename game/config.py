# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""Game configuration loaded from ~/.pnhrc (JSON)."""

from __future__ import annotations

__version__ = "0.1.0"

import json
import os
import sys

from game.game_defs import (
    find_role, find_race, is_valid_alignment,
    is_valid_combination, alignment_to_string,
)


class GameConfig:
    """Player identity loaded from ``~/.pnhrc``.

    Missing or invalid fields fall back to safe defaults.
    """

    def __init__(self) -> None:
        self.name: str = "Unknown Player"
        self.role: str = "Caveman"
        self.race: str = "Human"
        self.alignment: str = "Neutral"

    @staticmethod
    def _config_path() -> str:
        """Resolve ``~/.pnhrc`` to an absolute path."""
        home = os.environ.get("HOME", ".")
        return os.path.join(home, ".pnhrc")

    def load(self) -> bool:
        """Read ``~/.pnhrc``.  Creates a default template if missing.

        Returns True if the file was found and parsed.
        """
        path = self._config_path()
        if not os.path.isfile(path):
            self.write_default()
            return False

        try:
            with open(path, "r") as f:
                j = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: {path}: {e}", file=sys.stderr)
            print("Using defaults.", file=sys.stderr)
            return False

        self.name = j.get("name", self.name)
        self.role = j.get("role", self.role)
        self.race = j.get("race", self.race)
        self.alignment = j.get("alignment", self.alignment)
        self._validate()
        return True

    def _validate(self) -> None:
        """Clamp invalid config values back to supported options."""
        if find_role(self.role) is None:
            print(f'Warning: unknown role "{self.role}", defaulting to Caveman.',
                  file=sys.stderr)
            self.role = "Caveman"

        if find_race(self.race) is None:
            print(f'Warning: unknown race "{self.race}", defaulting to Human.',
                  file=sys.stderr)
            self.race = "Human"

        if not is_valid_alignment(self.alignment):
            print(f'Warning: unknown alignment "{self.alignment}", '
                  "defaulting to Neutral.", file=sys.stderr)
            self.alignment = "Neutral"

        if not is_valid_combination(self.role, self.race, self.alignment):
            print(f"Warning: {self.race} {self.role} ({self.alignment}) "
                  "is not a valid combination.", file=sys.stderr)
            self.race = "Human"
            rd = find_role(self.role)
            if rd and rd.allowed_alignments:
                self.alignment = alignment_to_string(rd.allowed_alignments[0])
            else:
                self.alignment = "Neutral"
            print(f"Falling back to Human {self.role} ({self.alignment}).",
                  file=sys.stderr)

    def write_default(self) -> bool:
        """Write a starter config file for first-time players."""
        path = self._config_path()
        try:
            with open(path, "w") as f:
                json.dump({
                    "name": "Unknown Player",
                    "role": "Caveman",
                    "race": "Human",
                    "alignment": "Neutral",
                }, f, indent=4)
                f.write("\n")
            return True
        except OSError:
            return False
