#include <stdint.h>
#include <stddef.h>

uint8_t checksum8(const uint8_t *buffer, size_t length) {
    uint32_t sum = 0;
    for (size_t i = 0; i < length; i++) {
        sum += buffer[i];
    }
    return (uint8_t)(sum & 0xFF);
}
