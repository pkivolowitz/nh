# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""NetHack 3.6 roles, races, and alignments for character creation."""

from __future__ import annotations

__version__ = "0.1.0"

from enum import Enum
from typing import Optional


class Alignment(Enum):
    """The three NetHack 3.6 alignments."""
    LAWFUL = "Lawful"
    NEUTRAL = "Neutral"
    CHAOTIC = "Chaotic"


class RoleDef:
    """Character class with allowed races and alignments."""

    __slots__ = ("name", "allowed_races", "allowed_alignments")

    def __init__(self, name: str, allowed_races: list[str],
                 allowed_alignments: list[Alignment]) -> None:
        self.name: str = name
        self.allowed_races: list[str] = allowed_races
        self.allowed_alignments: list[Alignment] = allowed_alignments


class RaceDef:
    """Playable race with allowed alignments."""

    __slots__ = ("name", "allowed_alignments")

    def __init__(self, name: str,
                 allowed_alignments: list[Alignment]) -> None:
        self.name: str = name
        self.allowed_alignments: list[Alignment] = allowed_alignments


# ---- static data ---------------------------------------------------------

_ROLES: list[RoleDef] = [
    RoleDef("Archeologist", ["Human", "Dwarf", "Gnome"],
            [Alignment.LAWFUL, Alignment.NEUTRAL]),
    RoleDef("Barbarian", ["Human", "Orc"],
            [Alignment.NEUTRAL, Alignment.CHAOTIC]),
    RoleDef("Caveman", ["Human", "Dwarf", "Gnome"],
            [Alignment.LAWFUL, Alignment.NEUTRAL]),
    RoleDef("Healer", ["Human", "Gnome"],
            [Alignment.NEUTRAL]),
    RoleDef("Knight", ["Human"],
            [Alignment.LAWFUL]),
    RoleDef("Monk", ["Human"],
            [Alignment.LAWFUL, Alignment.NEUTRAL, Alignment.CHAOTIC]),
    RoleDef("Priest", ["Human", "Elf"],
            [Alignment.LAWFUL, Alignment.NEUTRAL, Alignment.CHAOTIC]),
    RoleDef("Ranger", ["Human", "Elf", "Gnome", "Orc"],
            [Alignment.NEUTRAL, Alignment.CHAOTIC]),
    RoleDef("Rogue", ["Human", "Orc"],
            [Alignment.CHAOTIC]),
    RoleDef("Samurai", ["Human"],
            [Alignment.LAWFUL]),
    RoleDef("Tourist", ["Human"],
            [Alignment.NEUTRAL]),
    RoleDef("Valkyrie", ["Human", "Dwarf"],
            [Alignment.LAWFUL, Alignment.NEUTRAL]),
    RoleDef("Wizard", ["Human", "Elf", "Gnome", "Orc"],
            [Alignment.NEUTRAL, Alignment.CHAOTIC]),
]

_RACES: list[RaceDef] = [
    RaceDef("Human", [Alignment.LAWFUL, Alignment.NEUTRAL, Alignment.CHAOTIC]),
    RaceDef("Elf",   [Alignment.CHAOTIC]),
    RaceDef("Dwarf", [Alignment.LAWFUL]),
    RaceDef("Gnome", [Alignment.NEUTRAL]),
    RaceDef("Orc",   [Alignment.CHAOTIC]),
]


# ---- lookup helpers -------------------------------------------------------

def _ci_eq(a: str, b: str) -> bool:
    """Case-insensitive string comparison."""
    return a.casefold() == b.casefold()


def alignment_to_string(a: Alignment) -> str:
    """Convert an alignment enum to its display name."""
    return a.value


def string_to_alignment(s: str) -> Alignment:
    """Parse a user-facing alignment string.  Defaults to Neutral."""
    for a in Alignment:
        if _ci_eq(s, a.value):
            return a
    return Alignment.NEUTRAL


def is_valid_alignment(s: str) -> bool:
    """Return True if *s* names a supported alignment."""
    return any(_ci_eq(s, a.value) for a in Alignment)


def find_role(name: str) -> Optional[RoleDef]:
    """Look up a role by name (case-insensitive)."""
    for r in _ROLES:
        if _ci_eq(r.name, name):
            return r
    return None


def find_race(name: str) -> Optional[RaceDef]:
    """Look up a race by name (case-insensitive)."""
    for r in _RACES:
        if _ci_eq(r.name, name):
            return r
    return None


def is_valid_combination(role_name: str, race_name: str,
                         align_name: str) -> bool:
    """Validate a role / race / alignment triple."""
    role = find_role(role_name)
    race = find_race(race_name)
    if role is None or race is None:
        return False
    # Race must be allowed for this role.
    if not any(_ci_eq(rn, race_name) for rn in role.allowed_races):
        return False
    if not is_valid_alignment(align_name):
        return False
    a = string_to_alignment(align_name)
    return a in role.allowed_alignments and a in race.allowed_alignments


def get_all_roles() -> list[RoleDef]:
    """Return the full list of playable roles."""
    return _ROLES


def get_all_races() -> list[RaceDef]:
    """Return the full list of playable races."""
    return _RACES
