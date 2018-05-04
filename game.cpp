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
	assert(p != nullptr);
	int c;
	bool keep_going = true;

	while (keep_going) {
		c = p->GetKey();
		switch (c) {
			case 'q':
				if (HandleQuit())
					keep_going = false;
				break;
		}
	}
}

void Game::Run(string & error) {
	ENTERING();
	try {
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
	p->KeyMode(KeyModes::INTERACTIVE);
	p->AddString((char *) "Quit? (y|n): ");
	p->Refresh();
	retval = (tolower(p->GetKey()) == 'y');
	p->AddString(nullptr, 0, 0, true, true);
	p->KeyMode(KeyModes::NONINTERACTIVE);
	RETURNING(retval);
	return retval;
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
