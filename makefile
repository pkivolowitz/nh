SYS := $(shell g++ -dumpmachine)
ifneq (, $(findstring apple, $(SYS)))
CFLAGS	= -Wall -Iinclude -std=c++17 -g -I/usr/local/opt/ncurses/include
else
CFLAGS	= -Wall -Iinclude -std=c++17 -g -I/usr/local/opt/ncurses/include
endif

CC	    = g++
LFLAGS=-L/opt/homebrew/opt/ncurses/lib -lmenu -lncurses

srcs = $(wildcard src/*.cpp)
objs = $(srcs:.cpp=.o)
deps = $(srcs:.cpp=.d)

pnh: $(objs)
	$(CC) $^ -o $@ $(LFLAGS)

%.o: %.cpp
	$(CC) -MMD -MP $(CFLAGS) -c $< -o $@

.PHONY: clean

# $(RM) is rm -f by default
clean:
	$(RM) $(objs) $(deps) pnh core

-include $(deps)
