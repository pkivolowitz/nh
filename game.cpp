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
	while (ri > levels.begin()) {
		ri--;
		delete *ri;
		levels.erase(ri);
		log << __FILE__ << " " << __FUNCTION__ << " " << __LINE__ << " deleted level" << endl;	
	}
	LEAVING();
}

bool Game::Initialize(Presentation * pr, string & error) {
	ENTERING();
	bool retval = true;
	error = "";
	assert(pr != nullptr);
	p = pr;
	RETURNING(retval);
	return retval;
}

void Game::EventLoop() {
	/*	Initial assertions:
		We must be connected to the presentation class.
		There must be at least one layer in the game.
	*/

	assert(p != nullptr);
	assert(levels.size() > 0);
	int c;
	bool keep_going = true;

	while (keep_going) {
		bool needs_refresh = false;
		c = p->GetKey();
		switch (c) {
			case 'q':
				if (HandleQuit())
					keep_going = false;
				break;

			case 22: // This keycode is ^V
				HandleVersion();
				break;
		}
		if (UpdateClock())
			needs_refresh = true;
		if (needs_refresh) {
			p->Refresh();
		} else {
			Delay();
		}
	}
}

void Game::Run(string & error) {
	ENTERING();
	try {
		AddLevel();
		EventLoop();
	}
	catch (string e) {
		error = e;
	}
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
	string v = string("pnh - version 0.0.0 - ") + string(__DATE__) + string(" [any key to continue]");

	p->KeyMode(KM_RAW | KM_NOECHO | KM_NOCURS);
	p->AddString(v);
	p->Refresh();
	p->GetKey();
	p->AddString(nullptr, 0, 0, true, true);
	p->KeyMode(KM_NONINTERACTIVE);
	LEAVING();
}

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
	int lines, cols;

	p->GetDimensions(lines, cols);
	l->Initialize(lines, cols);
	levels.push_back(l);
	LEAVING();
}
