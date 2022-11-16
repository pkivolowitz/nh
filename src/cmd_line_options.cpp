#include <string>
#include <iostream>
#include <getopt.h>

using namespace std;

extern bool no_corridors;
extern bool StartLog();
extern int32_t seed;

bool HandleOptions(
	int argc, 
	char **argv, 
	string & player_name)
{
	int c;
	bool retval = true;
	while ((c = getopt(argc, argv, "n:cs:hl")) != -1) {
		switch (c) {
		case 'h':
			cout << "Usage:\n";
			cout << "-c no corridors\n";
			cout << "-h prints this help\n";
			cout << "-l enables logging\n";
			cout << "-n sets player name\n";
			cout << "-s specifies random seed (omit for time of day)\n";
			retval = false;
			break;

		case 'c':
			no_corridors = true;
			break;

		case 'n':
			player_name = string(optarg);
			break;

		case 's':
			srand((seed = atoi(optarg)));
			break;

		case 'l':
			if (!StartLog())
				return 1;
			break;
		}
	}
	if (player_name.empty()) {
		player_name = "Unknown Player";
	}
	return retval;
}

