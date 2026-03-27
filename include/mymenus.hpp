// Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

#pragma once
#include <unistd.h>
#include <menu.h>
#include <string>
#include <vector>

using ItemVector = std::vector<std::string>;

class MyMenu {
public:
    // Initialize menu-owned pointers and allocate the MENU handle.
    MyMenu();
    // Release menu-owned ncurses resources.
    virtual ~MyMenu();

    // Build a menu from the provided item strings.
    bool Initialize(ItemVector & );
    // Return the width of the widest item label.
    int MaxItemWidth(ItemVector &);

    MENU * m;
    ITEM * current_item;
    ITEM ** items;

    int lines;
    int cols;

    static const int MAX_COLS = 30;
    static const int MAX_LINES = 20;

};
