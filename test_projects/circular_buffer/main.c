#include <stdio.h>
#include "cbuf.h"

int main(void) {
    CircularBuffer cb;
    cbuf_init(&cb);

    printf("Writing 10 through 60 into buffer...\n");
    for (int i = 1; i <= 6; i++)
        cbuf_write(&cb, i * 10);

    printf("Buffer (%d/%d): ", cbuf_count(&cb), CBUF_CAPACITY);
    cbuf_display(&cb);

    int val;
    printf("\nReading 3 values: ");
    for (int i = 0; i < 3; i++) {
        cbuf_read(&cb, &val);
        printf("%d ", val);
    }
    printf("\n");

    printf("Writing 70 and 80 after partial drain...\n");
    cbuf_write(&cb, 70);
    cbuf_write(&cb, 80);

    printf("Buffer (%d/%d): ", cbuf_count(&cb), CBUF_CAPACITY);
    cbuf_display(&cb);

    printf("\nDraining buffer: ");
    while (!cbuf_is_empty(&cb)) {
        cbuf_read(&cb, &val);
        printf("%d ", val);
    }
    printf("\n\n");

    printf("Read from empty buffer: %s\n",
           cbuf_read(&cb, &val) == 0 ? "succeeded" : "correctly rejected");

    return 0;
}
