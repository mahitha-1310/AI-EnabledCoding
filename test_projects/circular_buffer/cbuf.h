#ifndef CBUF_H
#define CBUF_H

#define CBUF_CAPACITY 8

typedef struct {
    int data[CBUF_CAPACITY];
    int head;
    int tail;
    int count;
} CircularBuffer;

void cbuf_init(CircularBuffer *cb);
int cbuf_write(CircularBuffer *cb, int value);
int cbuf_read(CircularBuffer *cb, int *out);
int cbuf_is_empty(const CircularBuffer *cb);
int cbuf_is_full(const CircularBuffer *cb);
int cbuf_count(const CircularBuffer *cb);
void cbuf_display(const CircularBuffer *cb);

#endif
