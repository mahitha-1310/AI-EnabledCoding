CC = clang
CFLAGS = -std=c99 -Wall -Wextra
EXECUTABLE = strutil_demo

all: $(EXECUTABLE)

$(EXECUTABLE): main.c strutil.c strutil.h
	$(CC) $(CFLAGS) main.c strutil.c -o $(EXECUTABLE)

clean:
	rm -f $(EXECUTABLE)
