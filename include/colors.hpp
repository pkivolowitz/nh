#pragma once

enum PNH_COLORS {
    CLR_EMPTY = 1,
    CLR_PLAYER,
    CLR_WALLS,
    CLR_CORRIDORS,
	CLR_SPELLBOOKS
};

struct CursesColorSupport {
    void Initialize();
};
