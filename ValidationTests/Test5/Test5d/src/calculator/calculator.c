/*
 * calculator.c
 *
 * Implements safe integer calculator operations.
 * Each operation returns a status code instead of crashing.
 */

#include "../../include/calculator.h"
#include "../../include/validation.h"

int safe_add(int a, int b, int *output) {
    if (!is_valid_output_pointer(output)) {
        return -1;
    }

    *output = a + b;
    return 0;
}

int safe_subtract(int a, int b, int *output) {
    if (!is_valid_output_pointer(output)) {
        return -1;
    }

    *output = a - b;
    return 0;
}

int safe_multiply(int a, int b, int *output) {
    if (!is_valid_output_pointer(output)) {
        return -1;
    }

    *output = a * b;
    return 0;
}

int safe_divide(int a, int b, int *output) {
    if (!is_valid_output_pointer(output)) {
        return -1;
    }

    if (!is_valid_denominator(b)) {
        return -2;
    }

    *output = a / b;
    return 0;
}
