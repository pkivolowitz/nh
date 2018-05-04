#include <iostream>
#include <fstream>
#include <string>
#include <cassert>
#include <unistd.h>

#include "game.hpp"

using namespace std;

extern ofstream log;

Game::Game() {
	p = nullptr;
	log << __FILE__ << " " << __FUNCTION__ << " " << __LINE__ << endl;	
}

Game::~Game() {
	assert(levels.size() == 0);
}

void Game::End() {
	auto ri = levels.end();
	while (ri > levels.begin()) {
		ri--;
		delete *ri;
		levels.erase(ri);
		log << __FILE__ << " " << __FUNCTION__ << " " << __LINE__ << endl;	
	}
	log << __FILE__ << " " << __FUNCTION__ << " " << __LINE__ << endl;	
}

bool Game::Initialize(Presentation * pr, string & error) {
	log << __FILE__ << " " << __FUNCTION__ << " " << __LINE__ << endl;	
	error = "";
	assert(pr != nullptr);
	p = pr;
	return true;
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
	try {
		EventLoop();
	}
	catch (string e) {
		error = e;
	}
}

bool Game::HandleQuit() {
	bool retval = false;
	wmove(stdscr, 0, 0);
	clrtoeol();
	p->KeyMode(KeyModes::INTERACTIVE);
	addstr("Quit? (y|n): ");
	refresh();
	sleep(2);
	p->KeyMode(KeyModes::NONINTERACTIVE);
	return retval = true;
}


void Game::AddLevel() {
	log << __FILE__ << " " << __FUNCTION__ << " " << __LINE__ << endl;	
	assert(p != nullptr);

	Level * l = new Level();
	int lines, cols;

	p->GetDimensions(lines, cols);
	l->Initialize(lines, cols);
	levels.push_back(l);
	log << __FILE__ << " " << __FUNCTION__ << " " << __LINE__ << endl;	
}
