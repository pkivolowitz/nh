#include <iostream>
#include "presentation.hpp"
#include "game.hpp"
#include "level.hpp"
#include "player.hpp"

using namespace std;

int main(int argc, char * argv[]) {
	Presentation p;
	Game g;
	vector<Player> players;

	string error;

	if (p.Initialize(error) && g.Initialize(p, error)) {
	}
	else {
		cerr << "Curses failed to initialize. Why:\n";
		cerr << error << endl;
	}

	return 0;
}
