/*
 * text.c
 *
 * Implements basic string utility functions.
 * This file should be discovered recursively by your unit testing stage.
 */

#include "text.h"

int string_length(const char *text) {
    /*
     * Treat NULL as an empty string for safe behavior.
     */
    int count = 0;

    if (text == 0) {
        return 0;
    }

    /*
     * Count characters until the null terminator is reached.
     */
    while (text[count] != '\0') {
        count++;
    }

    return count;
}

int is_empty(const char *text) {
    /*
     * A string is considered empty if it is NULL or starts immediately
     * with the null terminator.
     */
    return text == 0 || text[0] == '\0';
}
