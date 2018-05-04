#pragma once
#include <fstream>

extern std::ofstream log;

#define	ENTERING()			if (log.is_open()) log << __FILE__ << " " << __FUNCTION__ << " " << __LINE__ << " entering" << endl
#define	LEAVING()			if (log.is_open()) log << __FILE__ << " " << __FUNCTION__ << " " << __LINE__ << " leaving" << endl
#define RETURNING(r)		if (log.is_open()) log << __FILE__ << " " << __FUNCTION__ << " " << __LINE__ << " returning " << (r) << endl
	
