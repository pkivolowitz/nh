// Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

#include "game_time.hpp"

using namespace std;

// Construct the lightweight wall-clock helper.
GameTime::GameTime() {
}

// Return the current local time in HH:MM:SS format.
string GameTime::GetCurrentTime() {
	struct timeval tv;
	time_t nowtime;
	struct tm *nowtm;
	char tmbuf[64] = { 0 };

	gettimeofday(&tv, nullptr);
	nowtime = tv.tv_sec;
	nowtm = localtime(&nowtime);
	strftime(tmbuf, sizeof tmbuf, "%H:%M:%S", nowtm);
	return string(tmbuf);
}
