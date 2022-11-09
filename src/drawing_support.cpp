#include "drawing_support.hpp"

CornerMap corner_map;

/*	InitializeCornerMap - choosing to use the line drawing characters
	imposes a heavy burden that NetHack, rogue, etc. does not share.
	Using the line drawing characters requires more than 100 special
	cases in order to render corners and tees correctly.

	The method used is to scan the 3x3 region around each character
	in the freshly made level (prior to populating) building a nine
	character characterization of the region. This characterization
	is fed into a map which returns the special case line drawing
	character.
*/
void InitializeCornerMap() {
	corner_map["    HH VF"] = ACS_ULCORNER;
	corner_map["   HH FV "] = ACS_URCORNER;
	corner_map[" VFHHFFFF"] = ACS_LRCORNER;
	corner_map[" VF HH   "] = ACS_LLCORNER;
	corner_map["FV HH    "] = ACS_LRCORNER;
	corner_map[" VF HHHH "] = ACS_LLCORNER;
	corner_map["FFFFHHFV "] = ACS_ULCORNER;
	corner_map["FFFFVHFV "] = ACS_ULCORNER;
	corner_map["FV FVHFFF"] = ACS_LLCORNER;
	corner_map[" HHHH FV "] = ACS_URCORNER;
	corner_map["FFFHHF VF"] = ACS_URCORNER;
	corner_map["FFFFHHHH "] = ACS_ULCORNER;
	corner_map["FHHHH    "] = ACS_LRCORNER;
	corner_map["    HHHVF"] = ACS_ULCORNER;
	corner_map[" HHHVFFFF"] = ACS_LRCORNER;
	corner_map["HVFFHFFVF"] = ACS_VLINE;
	corner_map["FV FH FV "] = ACS_VLINE;
	corner_map["FVFHVF HH"] = ACS_RTEE;
	corner_map["FV FVHHFF"] = ACS_LLCORNER;
	corner_map["FVHFHFFFF"] = ACS_VLINE;
	corner_map["FFVHHF VF"] = ACS_URCORNER;
	corner_map["FFVFVHFV "] = ACS_ULCORNER;
	corner_map["FV VH V  "] = ACS_LRCORNER;
	corner_map[" VFHVFFHF"] = ACS_RTEE;
	corner_map["FV FVHFHF"] = ACS_LTEE;
	corner_map["HVF HH   "] = ACS_LLCORNER;
	corner_map["FFFHVF VF"] = ACS_URCORNER;
	corner_map[" VFHVFFFH"] = ACS_LRCORNER;
	corner_map["VFFFHHFV "] = ACS_ULCORNER;
	corner_map["    HHHHF"] = ACS_ULCORNER;
	corner_map[" HHHHFFFF"] = ACS_LRCORNER;
	corner_map["   HHHFVF"] = ACS_TTEE;
	corner_map["FVFHVF VF"] = ACS_RTEE;
	corner_map["  V HH VF"] = ACS_ULCORNER;
	corner_map[" VFHHFVFF"] = ACS_LRCORNER;
	corner_map[" VF HHH  "] = ACS_LLCORNER;
	corner_map["  HHH FHH"] = ACS_URCORNER;
	corner_map["HH FHHFFF"] = ACS_LLCORNER;
	corner_map["FFFFVVFVV"] = ACS_ULCORNER;
	corner_map["FFFVVFVVF"] = ACS_URCORNER;
	corner_map["FV HH   H"] = ACS_LRCORNER;
	corner_map["H   HH VF"] = ACS_ULCORNER;
	corner_map["    HH HF"] = ACS_ULCORNER;
	corner_map[" VFHVFFFF"] = ACS_LRCORNER;
	corner_map[" HH HF VF"] = ACS_VLINE;
	corner_map[" VF HV  V"] = ACS_LLCORNER;
	corner_map["VFFHVF VF"] = ACS_URCORNER;
	corner_map["FV FHHFFF"] = ACS_LLCORNER;
	corner_map[" VF HF VF"] = ACS_VLINE;
	corner_map["FFVFVHHH "] = ACS_ULCORNER;
	corner_map["FV VH H  "] = ACS_LRCORNER;
	corner_map["FVHHH    "] = ACS_LRCORNER;
	corner_map[" VFHHFFVF"] = ACS_RTEE;
	corner_map["FVFFVHFVH"] = ACS_LTEE;
	corner_map["FVHFVHFVF"] = ACS_LTEE;
	corner_map["FFFHHHHVF"] = ACS_TTEE;
	corner_map["HHHHHVFVV"] = ACS_URCORNER;
	corner_map["FVVHHV  V"] = ACS_BTEE;
	corner_map["FV HHHFFF"] = ACS_BTEE;
	corner_map["FFVFHHFHH"] = ACS_ULCORNER;
	corner_map["FHHFHHFFF"] = ACS_LLCORNER;
	corner_map["FV HH HHH"] = ACS_LRCORNER;
	corner_map["FFVFHHFV "] = ACS_ULCORNER;
	corner_map["FV HH V  "] = ACS_LRCORNER;
	corner_map["   HH FHH"] = ACS_URCORNER;
	corner_map["HH FHHFFF"] = ACS_LLCORNER;
	corner_map["FV HH HH "] = ACS_LRCORNER;
	corner_map["HH HH FV "] = ACS_URCORNER;
	corner_map["HHH HH VF"] = ACS_ULCORNER;
	corner_map["FV FVHFVF"] = ACS_LTEE;
	corner_map["FVFHHF VF"] = ACS_RTEE;
	corner_map["  V HV VF"] = ACS_ULCORNER;
	corner_map[" VFHVFVFF"] = ACS_LRCORNER;
	corner_map["FFFHVF HH"] = ACS_URCORNER;
	corner_map["FV FVHFFV"] = ACS_LLCORNER;
	corner_map["V  VH FV "] = ACS_URCORNER;
	corner_map["FV HHH VF"] = ACS_PLUS;
	corner_map[" VF HH VF"] = ACS_LTEE;
	corner_map["FFFHHHFV "] = ACS_TTEE;
	corner_map["  VHHVFVV"] = ACS_TTEE;
	corner_map["FVVFVHFV "] = ACS_LTEE;
	corner_map["VVFVHHV  "] = ACS_BTEE;
	corner_map[" VFHVFVHH"] = ACS_RTEE;
	corner_map[" VFHVFVVF"] = ACS_RTEE;
	corner_map["  VHHVFVH"] = ACS_TTEE;
	corner_map["HVFVHHV  "] = ACS_BTEE;
	corner_map["HHVFVHFV "] = ACS_LTEE;
	corner_map["FVVFVHHH "] = ACS_LTEE;
	corner_map["   HH FVH"] = ACS_URCORNER;
	corner_map["HH FVHFFF"] = ACS_LLCORNER;
	corner_map["VVFVHHH  "] = ACS_BTEE;
	corner_map["FVFHHF HH"] = ACS_RTEE;
	corner_map["HHF HH   "] = ACS_LLCORNER;
	corner_map[" VFHHHVFF"] = ACS_BTEE;
	corner_map["FV HHHFFV"] = ACS_BTEE;
	corner_map["V  HH FV "] = ACS_URCORNER;
	corner_map[" HHHVFFVF"] = ACS_RTEE;
	corner_map[" VF HH HH"] = ACS_LLCORNER;
	corner_map[" HH HH VF"] = ACS_ULCORNER;
	corner_map["HHHHH FV "] = ACS_URCORNER;
	corner_map["   HHHFVV"] = ACS_TTEE;
	corner_map["   HHHVVF"] = ACS_TTEE;
	corner_map["H  VHHVVF"] = ACS_ULCORNER;
	corner_map["FVVHHV  H"] = ACS_LRCORNER;
	corner_map["FFFHHH VF"] = ACS_TTEE;
	corner_map["FFVHHHFV "] = ACS_TTEE;
	corner_map[" VF HHHHH"] = ACS_LLCORNER;
	corner_map["FFFFHVFVV"] = ACS_ULCORNER;
	corner_map["FFFHVFVVF"] = ACS_URCORNER;
	corner_map["FV HHH  V"] = ACS_BTEE;
	corner_map["V  HHH VF"] = ACS_TTEE;
	corner_map["FFFHHF HH"] = ACS_URCORNER;
	corner_map["FV FHHFFV"] = ACS_LLCORNER;
	corner_map[" VF HH  V"] = ACS_LLCORNER;
	corner_map["VFFHHF VF"] = ACS_URCORNER;
	corner_map["FVVHHH   "] = ACS_BTEE;
	corner_map["VVFHHH   "] = ACS_BTEE;
	corner_map[" VFHHHFV "] = ACS_PLUS;
	corner_map["FV FVHFVV"] = ACS_LTEE;
	corner_map["  H HV VF"] = ACS_ULCORNER;
	corner_map[" HHHVFVFF"] = ACS_LRCORNER;
	corner_map["FV FHHFVF"] = ACS_LTEE;
	corner_map["FVFHVFHVF"] = ACS_RTEE;
	corner_map["HVFHVFFFH"] = ACS_LRCORNER;
	corner_map[" VF HF HH"] = ACS_VLINE;
	corner_map[" HF HH   "] = ACS_LLCORNER;
	corner_map["HH FVHFFV"] = ACS_LLCORNER;
	corner_map["   HH FVH"] = ACS_URCORNER;
	corner_map["H  VH FV "] = ACS_URCORNER;
	corner_map["V  VHHVV "] = ACS_TTEE;
	corner_map["FVVHHVV V"] = ACS_BTEE;
	corner_map["FFVFHHFV "] = ACS_ULCORNER;
	corner_map["V  VHHVVF"] = ACS_TTEE;
	corner_map["VVFHVF VF"] = ACS_RTEE;
	corner_map["   HH FH "] = ACS_URCORNER;
	corner_map["HH FH FV "] = ACS_VLINE;
	corner_map["FVFFHHFV "] = ACS_LTEE;
	corner_map["FV FHHHVF"] = ACS_LTEE;
	corner_map["FHHHVF VF"] = ACS_RTEE;
	corner_map[" HHHVFVVF"] = ACS_RTEE;
	corner_map["  HHHVFVV"] = ACS_TTEE;
	corner_map["VVFHVF VF"] = ACS_RTEE;
	corner_map[" VF HH  H"] = ACS_LLCORNER;
	corner_map["VFFHHF HH"] = ACS_URCORNER;
	corner_map["FVFFVHFHH"] = ACS_LTEE;
	corner_map["FV HH H  "] = ACS_LRCORNER;
	corner_map["FVHFHHFFF"] = ACS_LLCORNER;
	corner_map["FV FVHHHV"] = ACS_LTEE;
	corner_map["V  VHHHVF"] = ACS_TTEE;
	corner_map["FVHHHV  V"] = ACS_BTEE;
	corner_map["VHHHVF VF"] = ACS_RTEE;
	corner_map["HH FHHFVF"] = ACS_LTEE;
	corner_map["FVVHHHH  "] = ACS_BTEE;
	corner_map["FVVFHHHVF"] = ACS_LTEE;
	corner_map["VVFHHHVFF"] = ACS_BTEE;
	corner_map["FFFFHHFVH"] = ACS_ULCORNER;
	corner_map["FHHFVHFVV"] = ACS_LTEE;
	corner_map["HHHVHHVVF"] = ACS_TTEE;
	corner_map["FVVFVVFFV"] = ACS_LLCORNER;
	corner_map["VVFVVFFVF"] = ACS_RTEE;
	corner_map[" VFHVFFVF"] = ACS_RTEE;
	corner_map["FFVHHH VF"] = ACS_TTEE;
	corner_map["FV HHHVFF"] = ACS_BTEE;
	corner_map["VFFHHH VF"] = ACS_TTEE;
	corner_map["FFFFVHHH "] = ACS_ULCORNER;
	corner_map["FVFFHFFFF"] = ACS_VLINE;
	corner_map["FFVFHHFVF"] = ACS_ULCORNER;
	corner_map[" VF HV  H"] = ACS_LLCORNER;
	corner_map["VFFHVF HH"] = ACS_URCORNER;
	corner_map[" VFHHFFVH"] = ACS_RTEE;
	corner_map["HHFFVHFV "] = ACS_LTEE;
	corner_map[" VFHHHFFV"] = ACS_BTEE;
	corner_map["VFFHHHFV "] = ACS_TTEE;
	corner_map["FFVFHHFVV"] = ACS_ULCORNER;
	corner_map["FVFHHFVVF"] = ACS_RTEE;
	corner_map["FFFFVHFVH"] = ACS_ULCORNER;
	corner_map["  VHHHFVF"] = ACS_TTEE;
	corner_map["FV HH FV "] = ACS_RTEE;
	corner_map["H  HH FHH"] = ACS_URCORNER;
	corner_map["FV FH HH "] = ACS_VLINE;
	corner_map["FH HH    "] = ACS_LRCORNER;
	corner_map[" VF HVHHH"] = ACS_LLCORNER;
	corner_map["VFFHVFHHH"] = ACS_URCORNER;
	corner_map["HVFHHHFFF"] = ACS_BTEE;
	corner_map["FFFHVFFVF"] = ACS_URCORNER;
	corner_map["FHHFH HH "] = ACS_VLINE;
	corner_map["FFFFHHFH "] = ACS_ULCORNER;
	corner_map["   HHHFHH"] = ACS_TTEE;
	corner_map["   HHHHHF"] = ACS_TTEE;
	corner_map["HHHFHHFFF"] = ACS_LLCORNER;
	corner_map["HHHHHFFFF"] = ACS_LRCORNER;
	corner_map["FFFFVHVH "] = ACS_ULCORNER;
	corner_map["FVHVH H  "] = ACS_LRCORNER;
	corner_map["FVVFVVFFF"] = ACS_LLCORNER;
	corner_map["VVFVVFFFF"] = ACS_LRCORNER;
}
