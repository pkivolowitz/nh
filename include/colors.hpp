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
    void Initialize();
};
