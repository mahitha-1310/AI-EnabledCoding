CC = clang
CFLAGS = -std=c99 -Wall -Wextra
EXECUTABLE = cbuf_demo

all: $(EXECUTABLE)

$(EXECUTABLE): main.c cbuf.c cbuf.h
	$(CC) $(CFLAGS) main.c cbuf.c -o $(EXECUTABLE)

clean:
	rm -f $(EXECUTABLE)
