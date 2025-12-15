#include <stdint.h>
#include <stddef.h>

uint8_t checksum8(const uint8_t *buffer, size_t length) {
    uint8_t result = 0;
    for (size_t i = 0; i < length; i++) {
        result ^= buffer[i];
    }
    return result;
}
