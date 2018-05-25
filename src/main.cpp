#include <iostream>
#include <fstream>
#include <string>
#include <cstdlib>
#include <getopt.h>
#include <iomanip>
#include "presentation.hpp"
#include "game.hpp"
#include "level.hpp"
#include "logging.hpp"

using namespace std;

std::string TimeAsString() {
	time_t t = time(NULL);
	struct tm tm = *localtime(&t);
	std::stringstream ss;
	ss << setfill('0');
	ss << setw(2) << tm.tm_hour << ":" << setw(2) << tm.tm_min << ":" << setw(2) << tm.tm_sec;
	return ss.str();
}

ofstream _Log;

static bool StartLog() {
	string log_file_name("/tmp/nh_log.txt");
	_Log.open(log_file_name);
	if (!_Log.is_open()) {
		cerr << "Could not open log file " << log_file_name << ".\n";
	}
	return _Log.is_open();
}

static bool HandleOptions(int argc, char * argv[]) {
	int c;
	bool retval = true;
	while ((c = getopt(argc, argv, "s:hl")) != -1) {
		switch (c) {
			case 'h':
				cout << "Usage:\n";
				cout << "-h prints this help\n";
				cout << "-l enables logging\n";
				cout << "-s specifies random seed (omit for time of day)\n";
				retval = false;
				break;

			case 's':
				srand(atoi(optarg));
				break;

			case 'l':
				if (!StartLog())
					return 1;
				break;
		}
	}
	return retval;
}

int main(int argc, char * argv[]) {
	srand((unsigned int) time(nullptr));
	if (!HandleOptions(argc, argv))
		return 0;

	Game g;
	Presentation p;

	/*	p provides the presentation layer.
		g provides the game itself.
	*/

	try {
		p.Initialize();
		g.Initialize(&p);
		g.Run();
	}
	catch (string e) {
		cerr << "Exception occurred: " << e << endl;
		LOGMESSAGE(e);
	}

	g.End();
	p.End();

	if (_Log.is_open())
		_Log.close();

	return 0;
}
