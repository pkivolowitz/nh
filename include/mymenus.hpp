#pragma once
#include <unistd.h>
#include <menu.h>
#include <string>
#include <vector>

using ItemVector = std::vector<std::string>;

class MyMenu {
public:
    MyMenu();
    virtual ~MyMenu();

    bool Initialize(ItemVector & );
    int MaxItemWidth(ItemVector &);

    MENU * m;
    ITEM * current_item;
    ITEM ** items;

    int lines;
    int cols;

    static const int MAX_COLS = 30;
    static const int MAX_LINES = 20;

};
