#include <iostream>
#include <fstream>
#include <string>
#include "presentation.hpp"
#include "game.hpp"
#include "level.hpp"
#include "logging.hpp"

using namespace std;

ofstream log;

static bool StartLog() {
	string log_file_name("/tmp/nh_log.txt");
	log.open(log_file_name);
	if (!log.is_open()) {
		cerr << "Could not open log file " << log_file_name << ".\n";
	}
	return log.is_open();
}

int main(int argc, char * argv[]) {
	if (!StartLog())
		return 1;

	Game g;
	Presentation p;
	string error;

	/*	p provides the presentation layer.
		g provides the game itself.
	*/

	if (p.Initialize(error)) {
		if (g.Initialize(&p, error)) {
			g.Run(error);
		} else {
			cerr << "Game failed to initialize. Why:\n";
		}
	} else {
		cerr << "Curses failed to initialize. Why:\n";
	}

	g.End();
	p.End();

	if (error.size() > 0) {
		cerr << error << endl;
		log << error << endl;
	}

	log.close();
	return 0;
}
