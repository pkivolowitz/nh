CC		= g++
CFLAGS	= -Wall -std=c++2a -g
LFLAGS	= -lcurses

srcs = $(wildcard *.cpp)
objs = $(srcs:.cpp=.o)
deps = $(srcs:.cpp=.d)

pnh: $(objs)
	$(CC) $^ -o $@ $(LFLAGS)

%.o: %.cpp
	$(CC) -MMD -MP $(CFLAGS) -c $< -o $@

.PHONY: clean

# $(RM) is rm -f by default
clean:
	$(RM) $(objs) $(deps) pnh

-include $(deps)