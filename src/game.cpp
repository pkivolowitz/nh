#include <iostream>
#include <fstream>
#include <string>
#include <cassert>
#include <unistd.h>

#include "logging.hpp"
#include "game.hpp"

using namespace std;

Game::Game() {
	p = nullptr;
	current_level = 0;
}

Game::~Game() {
	assert(levels.size() == 0);
}

void Game::End() {
	ENTERING();
	auto ri = levels.end();
	int counter = levels.size();
	while (ri > levels.begin()) {
		ri--;
		counter--;
		delete *ri;
		levels.erase(ri);
		LOGMESSAGE("deleted level: " << counter);
	}
	LEAVING();
}

void Game::Initialize(Presentation * pr) {
	ENTERING();
	assert(pr != nullptr);
	p = pr;
	LEAVING();
}

void Game::EventLoop() {
	/*	Initial assertions:
		We must be connected to the presentation class.
		There must be at least one layer in the game.

		How Delay() is used - the event loop is using the TTY in non-blocking
		mode - I have no wish to suck a laptop's battery dry however. So, if
		something happens (needs_refresh is true) I go at full speed but if not
		I call Delay() which wraps the platform dependent sleep function. On
		Linux, usleep().
	*/

	assert(p != nullptr);
	assert(levels.size() > 0);
	int c;
	bool keep_going = true;

	while (keep_going) {
		bool status_needs_refresh = false;
		bool map_needs_refresh = false;

		c = p->GetKey();
		switch (c) {
			case 'q': // Ask user if they want to quit
				if (HandleQuit())
					keep_going = false;
				break;

			case 22: // This keycode is ^V - show version info
				HandleVersion();
				break;

			case 'r': // debugging - force map refresh;
				AddLevel();
				current_level++;
				map_needs_refresh = true;
				break;

			default:
				break;
		}
		if (UpdateClock())
			status_needs_refresh = true;
		if (status_needs_refresh || map_needs_refresh) {
			if (map_needs_refresh) {
				p->ClearMapArea();
				levels.at(current_level)->Render(p);
			}
			p->Refresh();
		} else {
			Delay();
		}
	}
}

void Game::Run() {
	ENTERING();
	AddLevel();
	levels.at(current_level)->Render(p);
	p->Refresh();
	EventLoop();
	LEAVING();
}

bool Game::HandleQuit() {
	ENTERING();
	assert(p != nullptr);
	bool retval = false;
	p->KeyMode(KM_RAW);
	p->AddString((char *) "Quit? (y|n): ");
	p->Refresh();
	retval = (tolower(p->GetKey()) == 'y');
	p->AddString(nullptr, 0, 0, true, true);
	p->KeyMode(KM_NONINTERACTIVE);
	RETURNING(retval);
	return retval;
}

void Game::HandleVersion() {
	ENTERING();
	assert(p != nullptr);
	string v = string("pnh - version 0.0.0 - ") + 
		string(__DATE__) + 
		string(" [any key]");

	p->KeyMode(KM_RAW | KM_NOECHO | KM_NOCURS);
	p->AddString(v);
	p->Refresh();
	p->GetKey();
	p->AddString(nullptr, 0, 0, true, true);
	p->KeyMode(KM_NONINTERACTIVE);
	LEAVING();
}

/*	Game::UpdateClock() - this method will return true only if the text of the
	onscreen clock has changed. This means that even if this method is called
	multiple times per secend, the screen will be refreshed one once per 
	second (due to time). This is important because it allows the event loop
	to sleep during relative inactivity.
*/
bool Game::UpdateClock() {
	assert(p != nullptr);
	bool retval;
	static string previous_time;
	string current_time = gt.GetCurrentTime();
	if ((retval = (current_time != previous_time))) {
		int l, c;
		p->GetDimensions(l, c);
		p->AddString(current_time, l - 1, c - 8, true); 
	}
	previous_time = current_time;
	return retval;
}

void Game::Delay(useconds_t d) {
	usleep(d);
}

void Game::AddLevel() {
	ENTERING();
	assert(p != nullptr);

	Level * l = new Level();

	l->Initialize(p);
	levels.push_back(l);
	LEAVING();
}
