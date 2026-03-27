// Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

#include "mymenus.hpp"

using namespace std;

MyMenu::MyMenu() {
    m = nullptr;
    current_item = nullptr;
    items = nullptr;
    m = new_menu(nullptr);
}

MyMenu::~MyMenu() {
    if (m) {
    }
}

bool MyMenu::Initialize(ItemVector & items) {
    bool retval = false;
    (void)MaxItemWidth(items);
    free_menu(m);
    return retval;
}

int MyMenu::MaxItemWidth(ItemVector & items) {
    int max_width = 0;

    for (auto & i : items) {
        if (i.size() > max_width) {
            max_width = i.size();
        }
    }
    return max_width;
}