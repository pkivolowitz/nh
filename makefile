# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

SYS := $(shell g++ -dumpmachine)
CFLAGS = -Wall -Werror -Iinclude -std=c++20 -g -I/opt/homebrew/opt/ncurses/include -I/opt/homebrew/include

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
