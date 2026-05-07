/*
 * validation.c
 *
 * Implements validation helpers used by the high-assurance calculator.
 */

#include <limits.h>
#include "../../include/validation.h"

int is_valid_output_pointer(const int *output) {
    return output != 0;
}

int is_valid_denominator(int denominator) {
    return denominator != 0;
}

int would_add_overflow(int a, int b) {
    if (b > 0 && a > INT_MAX - b) {
        return 1;
    }

    if (b < 0 && a < INT_MIN - b) {
        return 1;
    }

    return 0;
}

int would_subtract_overflow(int a, int b) {
    if (b < 0 && a > INT_MAX + b) {
        return 1;
    }

    if (b > 0 && a < INT_MIN + b) {
        return 1;
    }

    return 0;
}

int would_multiply_overflow(int a, int b) {
    if (a == 0 || b == 0) {
        return 0;
    }

    if (a > 0) {
        if (b > 0) {
            return a > INT_MAX / b;
        }

        return b < INT_MIN / a;
    }

    if (b > 0) {
        return a < INT_MIN / b;
    }

    return a < INT_MAX / b;
}
