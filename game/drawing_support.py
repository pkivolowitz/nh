# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""Corner map: 368 neighbourhood keys → line-drawing display constants.

The map is populated by ``initialize_corner_map`` which must be called
once at startup.  Each key is a 9-character string built from the 3×3
neighbourhood of a cell:

    ' ' = empty / out-of-bounds
    'F' = floor (room interior)
    'H' = horizontal wall
    'V' = vertical wall

Values are the curses-independent CH_* constants from ``constants.py``.
"""

from __future__ import annotations

__version__ = "0.1.0"

from game.constants import (
    CH_ULCORNER, CH_URCORNER, CH_LLCORNER, CH_LRCORNER,
    CH_TTEE, CH_BTEE, CH_LTEE, CH_RTEE, CH_PLUS,
    CH_HLINE, CH_VLINE,
)

# The map is module-level so every Board instance shares it.
corner_map: dict[str, int] = {}


def initialize_corner_map() -> None:
    """Populate the global corner map.

    Ported verbatim from the C++ ``InitializeCornerMap``.  Each entry
    maps a 9-char neighbourhood key to the display constant for the
    centre cell.
    """
    # fmt: off
    m = corner_map
    m.clear()
    m["    HH VF"] = CH_ULCORNER
    m["   HH FV "] = CH_URCORNER
    m[" VFHHFFFF"] = CH_LRCORNER
    m[" VF HH   "] = CH_LLCORNER
    m["FV HH    "] = CH_LRCORNER
    m[" VF HHHH "] = CH_LLCORNER
    m["FFFFHHFV "] = CH_ULCORNER
    m["FFFFVHFV "] = CH_ULCORNER
    m["FV FVHFFF"] = CH_LLCORNER
    m[" HHHH FV "] = CH_URCORNER
    m["FFFHHF VF"] = CH_URCORNER
    m["FFFFHHHH "] = CH_ULCORNER
    m["FHHHH    "] = CH_LRCORNER
    m["    HHHVF"] = CH_ULCORNER
    m[" HHHVFFFF"] = CH_LRCORNER
    m["HVFFHFFVF"] = CH_VLINE
    m["FV FH FV "] = CH_VLINE
    m["FVFHVF HH"] = CH_RTEE
    m["FV FVHHFF"] = CH_LLCORNER
    m["FVHFHFFFF"] = CH_VLINE
    m["FFVHHF VF"] = CH_URCORNER
    m["FFVFVHFV "] = CH_ULCORNER
    m["FV VH V  "] = CH_LRCORNER
    m[" VFHVFFHF"] = CH_RTEE
    m["FV FVHFHF"] = CH_LTEE
    m["HVF HH   "] = CH_LLCORNER
    m["FFFHVF VF"] = CH_URCORNER
    m[" VFHVFFFH"] = CH_LRCORNER
    m["VFFFHHFV "] = CH_ULCORNER
    m["    HHHHF"] = CH_ULCORNER
    m[" HHHHFFFF"] = CH_LRCORNER
    m["   HHHFVF"] = CH_TTEE
    m["FVFHVF VF"] = CH_RTEE
    m["  V HH VF"] = CH_ULCORNER
    m[" VFHHFVFF"] = CH_LRCORNER
    m[" VF HHH  "] = CH_LLCORNER
    m["  HHH FHH"] = CH_URCORNER
    m["HH FHHFFF"] = CH_LLCORNER
    m["FFFFVVFVV"] = CH_ULCORNER
    m["FFFVVFVVF"] = CH_URCORNER
    m["FV HH   H"] = CH_LRCORNER
    m["H   HH VF"] = CH_ULCORNER
    m["    HH HF"] = CH_ULCORNER
    m[" VFHVFFFF"] = CH_LRCORNER
    m[" HH HF VF"] = CH_VLINE
    m[" VF HV  V"] = CH_LLCORNER
    m["VFFHVF VF"] = CH_URCORNER
    m["FV FHHFFF"] = CH_LLCORNER
    m[" VF HF VF"] = CH_VLINE
    m["FFVFVHHH "] = CH_ULCORNER
    m["FV VH H  "] = CH_LRCORNER
    m["FVHHH    "] = CH_LRCORNER
    m[" VFHHFFVF"] = CH_RTEE
    m["FVFFVHFVH"] = CH_LTEE
    m["FVHFVHFVF"] = CH_LTEE
    m["FFFHHHHVF"] = CH_TTEE
    m["HHHHHVFVV"] = CH_URCORNER
    m["FVVHHV  V"] = CH_BTEE
    m["FV HHHFFF"] = CH_BTEE
    m["FFVFHHFHH"] = CH_ULCORNER
    m["FHHFHHFFF"] = CH_LLCORNER
    m["FV HH HHH"] = CH_LRCORNER
    m["FFVFHHFV "] = CH_ULCORNER
    m["FV HH V  "] = CH_LRCORNER
    m["   HH FHH"] = CH_URCORNER
    m["HH FHHFFF"] = CH_LLCORNER   # duplicate key — last write wins
    m["FV HH HH "] = CH_LRCORNER
    m["HH HH FV "] = CH_URCORNER
    m["HHH HH VF"] = CH_ULCORNER
    m["FV FVHFVF"] = CH_LTEE
    m["FVFHHF VF"] = CH_RTEE
    m["  V HV VF"] = CH_ULCORNER
    m[" VFHVFVFF"] = CH_LRCORNER
    m["FFFHVF HH"] = CH_URCORNER
    m["FV FVHFFV"] = CH_LLCORNER
    m["V  VH FV "] = CH_URCORNER
    m["FV HHH VF"] = CH_PLUS
    m[" VF HH VF"] = CH_LTEE
    m["FFFHHHFV "] = CH_TTEE
    m["  VHHVFVV"] = CH_TTEE
    m["FVVFVHFV "] = CH_LTEE
    m["VVFVHHV  "] = CH_BTEE
    m[" VFHVFVHH"] = CH_RTEE
    m[" VFHVFVVF"] = CH_RTEE
    m["  VHHVFVH"] = CH_TTEE
    m["HVFVHHV  "] = CH_BTEE
    m["HHVFVHFV "] = CH_LTEE
    m["FVVFVHHH "] = CH_LTEE
    m["   HH FVH"] = CH_URCORNER
    m["HH FVHFFF"] = CH_LLCORNER
    m["VVFVHHH  "] = CH_BTEE
    m["FVFHHF HH"] = CH_RTEE
    m["HHF HH   "] = CH_LLCORNER
    m[" VFHHHVFF"] = CH_BTEE
    m["FV HHHFFV"] = CH_BTEE
    m["V  HH FV "] = CH_URCORNER
    m[" HHHVFFVF"] = CH_RTEE
    m[" VF HH HH"] = CH_LLCORNER
    m[" HH HH VF"] = CH_ULCORNER
    m["HHHHH FV "] = CH_URCORNER
    m["   HHHFVV"] = CH_TTEE
    m["   HHHVVF"] = CH_TTEE
    m["H  VHHVVF"] = CH_TTEE
    m["FVVHHV  H"] = CH_LRCORNER
    m["FFFHHH VF"] = CH_TTEE
    m["FFVHHHFV "] = CH_TTEE
    m[" VF HHHHH"] = CH_LLCORNER
    m["FFFFHVFVV"] = CH_ULCORNER
    m["FFFHVFVVF"] = CH_URCORNER
    m["FV HHH  V"] = CH_BTEE
    m["V  HHH VF"] = CH_TTEE
    m["FFFHHF HH"] = CH_URCORNER
    m["FV FHHFFV"] = CH_LLCORNER
    m[" VF HH  V"] = CH_LLCORNER
    m["VFFHHF VF"] = CH_URCORNER
    m["FVVHHH   "] = CH_BTEE
    m["VVFHHH   "] = CH_BTEE
    m[" VFHHHFV "] = CH_PLUS
    m["FV FVHFVV"] = CH_LTEE
    m["  H HV VF"] = CH_ULCORNER
    m[" HHHVFVFF"] = CH_LRCORNER
    m["FV FHHFVF"] = CH_LTEE
    m["FVFHVFHVF"] = CH_RTEE
    m["HVFHVFFFH"] = CH_LRCORNER
    m[" VF HF HH"] = CH_VLINE
    m[" HF HH   "] = CH_LLCORNER
    m["HH FVHFFV"] = CH_LLCORNER
    m["   HH FVH"] = CH_URCORNER   # duplicate
    m["H  VH FV "] = CH_URCORNER
    m["V  VHHVV "] = CH_TTEE
    m["FVVHHVV V"] = CH_BTEE
    m["FFVFHHFV "] = CH_ULCORNER   # duplicate
    m["V  VHHVVF"] = CH_TTEE
    m["VVFHVF VF"] = CH_RTEE
    m["   HH FH "] = CH_URCORNER
    m["HH FH FV "] = CH_VLINE
    m["FVFFHHFV "] = CH_LTEE
    m["FV FHHHVF"] = CH_LTEE
    m["FHHHVF VF"] = CH_RTEE
    m[" HHHVFVVF"] = CH_RTEE
    m["  HHHVFVV"] = CH_TTEE
    m["VVFHVF VF"] = CH_RTEE   # duplicate
    m[" VF HH  H"] = CH_LLCORNER
    m["VFFHHF HH"] = CH_URCORNER
    m["FVFFVHFHH"] = CH_LTEE
    m["FV HH H  "] = CH_LRCORNER
    m["FVHFHHFFF"] = CH_LLCORNER
    m["FV FVHHHV"] = CH_LTEE
    m["V  VHHHVF"] = CH_TTEE
    m["FVHHHV  V"] = CH_BTEE
    m["VHHHVF VF"] = CH_RTEE
    m["HH FHHFVF"] = CH_LTEE
    m["FVVHHHH  "] = CH_BTEE
    m["FVVFHHHVF"] = CH_LTEE
    m["VVFHHHVFF"] = CH_BTEE
    m["FFFFHHFVH"] = CH_ULCORNER
    m["FHHFVHFVV"] = CH_LTEE
    m["HHHVHHVVF"] = CH_TTEE
    m["FVVFVVFFV"] = CH_LLCORNER
    m["VVFVVFFVF"] = CH_RTEE
    m[" VFHVFFVF"] = CH_RTEE
    m["FFVHHH VF"] = CH_TTEE
    m["FV HHHVFF"] = CH_BTEE
    m["VFFHHH VF"] = CH_TTEE
    m["FFFFVHHH "] = CH_ULCORNER
    m["FVFFHFFFF"] = CH_VLINE
    m["FFVFHHFVF"] = CH_ULCORNER
    m[" VF HV  H"] = CH_LLCORNER
    m["VFFHVF HH"] = CH_URCORNER
    m[" VFHHFFVH"] = CH_RTEE
    m["HHFFVHFV "] = CH_LTEE
    m[" VFHHHFFV"] = CH_BTEE
    m["VFFHHHFV "] = CH_TTEE
    m["FFVFHHFVV"] = CH_ULCORNER
    m["FVFHHFVVF"] = CH_RTEE
    m["FFFFVHFVH"] = CH_ULCORNER
    m["  VHHHFVF"] = CH_TTEE
    m["FV HH FV "] = CH_RTEE
    m["H  HH FHH"] = CH_URCORNER
    m["FV FH HH "] = CH_VLINE
    m["FH HH    "] = CH_LRCORNER
    m[" VF HVHHH"] = CH_LLCORNER
    m["VFFHVFHHH"] = CH_URCORNER
    m["HVFHHHFFF"] = CH_BTEE
    m["FFFHVFFVF"] = CH_URCORNER
    m["FHHFH HH "] = CH_VLINE
    m["FFFFHHFH "] = CH_ULCORNER
    m["   HHHFHH"] = CH_TTEE
    m["   HHHHHF"] = CH_TTEE
    m["HHHFHHFFF"] = CH_LLCORNER
    m["HHHHHFFFF"] = CH_LRCORNER
    m["FFFFVHVH "] = CH_ULCORNER
    m["FVHVH H  "] = CH_LRCORNER
    m["FVVFVVFFF"] = CH_LLCORNER
    m["VVFVVFFFF"] = CH_LRCORNER
    m["  VHHVFHH"] = CH_TTEE
    m[" VFHVFHHH"] = CH_RTEE
    m["HHVFHHFVF"] = CH_LTEE
    m["HVFHHHVFF"] = CH_BTEE
    m["FFFFHFFVF"] = CH_VLINE
    m["FV HHHHHH"] = CH_BTEE
    m["V  HHHHHF"] = CH_TTEE
    m["HHFHHFFVF"] = CH_RTEE
    m["FVFFHHHHH"] = CH_LTEE
    m["FHHHHH VF"] = CH_PLUS
    m["FVHHH HHH"] = CH_LRCORNER
    m[" VFHHHFVV"] = CH_PLUS
    m["VFFHHFVVF"] = CH_URCORNER
    m["V  HH FVH"] = CH_URCORNER
    m["FFFHHHFVH"] = CH_TTEE
    m["HHHFVHFVV"] = CH_LTEE
    m["FFFHVFHHH"] = CH_URCORNER
    m["H   HH HF"] = CH_ULCORNER
    m["FVVHHVVFF"] = CH_BTEE
    m["VVFHVFFFF"] = CH_LRCORNER
    m["  V HVHVF"] = CH_ULCORNER
    m[" HVHVFVVF"] = CH_RTEE
    m["FFFHVFHVF"] = CH_URCORNER
    m["HVFHVFFFF"] = CH_LRCORNER
    m["FV HHHV V"] = CH_BTEE
    m["FV FHHHFF"] = CH_LLCORNER
    m["FFHHHF VF"] = CH_URCORNER
    m["HHHHHHFVV"] = CH_TTEE
    m["HHHHHHVVF"] = CH_TTEE
    m["FFVFVVHHV"] = CH_ULCORNER
    m["FVFVVFHVF"] = CH_RTEE
    m["FFFHHHFVF"] = CH_TTEE
    m["FV FVHVHV"] = CH_LLCORNER
    m["V VVHVVVF"] = CH_TTEE
    m["FVVFVHFFV"] = CH_LLCORNER
    m["VVFVHFFVH"] = CH_RTEE
    m["FV FHHVFF"] = CH_LLCORNER
    m["FFHHVF VF"] = CH_URCORNER
    m["FV HH  HH"] = CH_LRCORNER
    m["HH  HH VF"] = CH_ULCORNER
    m["HVFFHFFFF"] = CH_VLINE
    m[" VFHVFVHF"] = CH_RTEE
    m["HVFVHFFFF"] = CH_LRCORNER
    m["HHVFVHFFF"] = CH_LLCORNER
    m["FVFFVHHH "] = CH_LTEE
    m["VVFHHV  V"] = CH_BTEE
    m["FFFFVHFFV"] = CH_HLINE
    m["FFVVHHFV "] = CH_TTEE
    m["FVFFVHFVV"] = CH_LTEE
    m["VFFVHHVVF"] = CH_TTEE
    m[" HH HHHHF"] = CH_ULCORNER
    m["HHHHVFFFF"] = CH_LRCORNER
    m[" VFHHFFFV"] = CH_LRCORNER
    m["FFHFHVFVV"] = CH_ULCORNER
    m["FHHHVFVVF"] = CH_RTEE
    m["HHF HHH  "] = CH_LLCORNER
    m["FV FVHHHF"] = CH_LTEE
    m["FVHHHF VF"] = CH_RTEE
    m[" VF HHHHF"] = CH_LTEE
    m["FVHFHFFVF"] = CH_VLINE
    m["FVVFHVFVF"] = CH_LTEE
    m["VVFHVFVFF"] = CH_LRCORNER
    m["H HHHVFVV"] = CH_TTEE
    m[" VF HV HH"] = CH_LLCORNER
    m["VFFHVFHHF"] = CH_URCORNER
    m["HVFHHFVFF"] = CH_LRCORNER
    m[" HV HH VF"] = CH_ULCORNER
    m["HVF HH  H"] = CH_LLCORNER
    # fmt: on
