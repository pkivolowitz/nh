#include <iostream>
#include "mymenus.hpp"

using namespace std;

ItemVector items;

void MakeItems() {
    items.push_back("Select one:");
    items.push_back("a) Foo");
    items.push_back("b) Bar");
    items.push_back("c) Baz");
}

void InitCurses() {
    initscr();
    start_color();
    use_default_colors();
    cbreak();
	noecho();
	keypad(stdscr, TRUE);
    curs_set(0);
}

void EndCurses() {
    curs_set(1);
    keypad(stdscr, FALSE);
    echo();
    nocbreak();
    endwin();
}

int main(int argc, char ** argv) {
    MyMenu menu;
    void FillScreen();

    MakeItems();

    InitCurses();
    FillScreen();
    refresh();

    if (menu.Initialize(items)) {       
    }
    
    sleep(5);
    EndCurses();
    return 0;
}

void FillScreen() {
    string text;
    text.resize(COLS);
    for (auto & c : text)
        c = '*';
    for (int row = 0; row < LINES; row++) {
        mvaddstr(row, 0, text.c_str());
    }
}
