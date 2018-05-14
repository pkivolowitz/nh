#pragma once
#include <fstream>

extern std::ofstream _Log;

#define	ENTERING()			if (_Log.is_open()) _Log << __FILE__ << " " << __FUNCTION__ << " " << __LINE__ << " entering" << endl
#define	LEAVING()			if (_Log.is_open()) _Log << __FILE__ << " " << __FUNCTION__ << " " << __LINE__ << " leaving" << endl
#define RETURNING(r)		if (_Log.is_open()) _Log << __FILE__ << " " << __FUNCTION__ << " " << __LINE__ << " returning " << (r) << endl
#define LOGMESSAGE(m)		if (_Log.is_open()) _Log << __FILE__ << " " << __FUNCTION__ << " " << __LINE__ << " " << m << endl

