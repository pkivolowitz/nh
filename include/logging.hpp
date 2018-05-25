#pragma once
#include <fstream>
#include <string>
#include <sstream>
#include <time.h>

extern std::ofstream _Log;
extern std::string TimeAsString();

#define	ENTERING()			if (_Log.is_open()) _Log << __FILE__ << " " << __FUNCTION__ << " " << __LINE__ << " entering " << TimeAsString() << endl
#define	LEAVING()			if (_Log.is_open()) _Log << __FILE__ << " " << __FUNCTION__ << " " << __LINE__ << " leaving " << TimeAsString() <<endl
#define RETURNING(r)		if (_Log.is_open()) _Log << __FILE__ << " " << __FUNCTION__ << " " << __LINE__ << " returning " << (r) << " " << TimeAsString() << endl
#define LOGMESSAGE(m)		if (_Log.is_open()) _Log << __FILE__ << " " << __FUNCTION__ << " " << __LINE__ << " " << m << " " << TimeAsString() << endl

