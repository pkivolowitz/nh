#pragma once

class Item {
	public:
		Item();

		char Symbol();

	private:
		char symbol;
};

typedef Item * ItemPtr;
