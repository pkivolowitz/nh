// Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

#pragma once

enum PNH_COLORS {
    CLR_EMPTY = 1,
    CLR_PLAYER,
    CLR_WALLS,
    CLR_CORRIDORS,
	CLR_SPELLBOOKS,
	CLR_DOORS
};

struct CursesColorSupport {
    // Register the color pairs used by the game UI.
    void Initialize();
};
