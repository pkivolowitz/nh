#include <iostream>
#include <fstream>
#include <string>
#include "presentation.hpp"
#include "game.hpp"
#include "level.hpp"
#include "player.hpp"

using namespace std;

ofstream log;

int main(int argc, char * argv[]) {
	string log_file_name("/tmp/nh_log.txt");
	log.open(log_file_name);
	if (!log.is_open()) {
		cerr << "Could not open log file " << log_file_name << ".\n";
		return 0;
	}

	Presentation p;
	Game g;
	vector<Player> players;

	string error;

	if (p.Initialize(error) && g.Initialize(&p, error)) {
		g.AddLevel();
	}
	else {
		cerr << "Curses failed to initialize. Why:\n";
		cerr << error << endl;
	}

	g.End();
	p.End();
	log.close();
	return 0;
}
