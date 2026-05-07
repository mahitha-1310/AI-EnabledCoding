CC = clang
CFLAGS = -std=c99 -Wall -Wextra
EXECUTABLE = stack_demo

all: $(EXECUTABLE)

$(EXECUTABLE): main.c stack.c stack.h
	$(CC) $(CFLAGS) main.c stack.c -o $(EXECUTABLE)

clean:
	rm -f $(EXECUTABLE)
