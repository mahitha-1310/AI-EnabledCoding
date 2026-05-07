#include <stdio.h>
#include "cbuf.h"

void cbuf_init(CircularBuffer *cb) {
    cb->head = 0;
    cb->tail = 0;
    cb->count = 0;
}

int cbuf_write(CircularBuffer *cb, int value) {
    if (cbuf_is_full(cb))
        return -1;
    cb->data[cb->tail] = value;
    cb->tail = (cb->tail + 1) % CBUF_CAPACITY;
    cb->count++;
    return 0;
}

int cbuf_read(CircularBuffer *cb, int *out) {
    if (cbuf_is_empty(cb))
        return -1;
    *out = cb->data[cb->head];
    cb->head = (cb->head + 1) % CBUF_CAPACITY;
    cb->count--;
    return 0;
}

int cbuf_is_empty(const CircularBuffer *cb) {
    return cb->count == 0;
}

int cbuf_is_full(const CircularBuffer *cb) {
    return cb->count == CBUF_CAPACITY;
}

int cbuf_count(const CircularBuffer *cb) {
    return cb->count;
}

void cbuf_display(const CircularBuffer *cb) {
    printf("[");
    for (int i = 0; i < cb->count; i++) {
        int idx = (cb->head + i) % CBUF_CAPACITY;
        printf("%d", cb->data[idx]);
        if (i < cb->count - 1)
            printf(", ");
    }
    printf("]\n");
}
