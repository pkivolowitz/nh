// Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

#include "mymenus.hpp"

using namespace std;

// Initialize menu pointers and create an empty MENU handle.
MyMenu::MyMenu() {
    m = nullptr;
    current_item = nullptr;
    items = nullptr;
    m = new_menu(nullptr);
}

// Tear down menu resources owned by this wrapper.
MyMenu::~MyMenu() {
    if (m) {
    }
}

// Prepare the menu state from the supplied item labels.
bool MyMenu::Initialize(ItemVector & items) {
    bool retval = false;
    (void)MaxItemWidth(items);
    free_menu(m);
    return retval;
}

// Measure the widest menu label for layout calculations.
int MyMenu::MaxItemWidth(ItemVector & items) {
    int max_width = 0;

    for (auto & i : items) {
        if (i.size() > max_width) {
            max_width = i.size();
        }
    }
    return max_width;
}
