/*
 * calculator.c
 *
 * Implements high-assurance safe integer calculator operations.
 */

#include "../../include/calculator.h"
#include "../../include/validation.h"

int safe_add(int a, int b, int *output) {
    if (!is_valid_output_pointer(output)) {
        return CALC_NULL_OUTPUT_ERROR;
    }

    if (would_add_overflow(a, b)) {
        return CALC_OVERFLOW_ERROR;
    }

    *output = a + b;
    return CALC_SUCCESS;
}

int safe_subtract(int a, int b, int *output) {
    if (!is_valid_output_pointer(output)) {
        return CALC_NULL_OUTPUT_ERROR;
    }

    if (would_subtract_overflow(a, b)) {
        return CALC_OVERFLOW_ERROR;
    }

    *output = a - b;
    return CALC_SUCCESS;
}

int safe_multiply(int a, int b, int *output) {
    if (!is_valid_output_pointer(output)) {
        return CALC_NULL_OUTPUT_ERROR;
    }

    if (would_multiply_overflow(a, b)) {
        return CALC_OVERFLOW_ERROR;
    }

    *output = a * b;
    return CALC_SUCCESS;
}

int safe_divide(int a, int b, int *output) {
    if (!is_valid_output_pointer(output)) {
        return CALC_NULL_OUTPUT_ERROR;
    }

    if (!is_valid_denominator(b)) {
        return CALC_DIVIDE_BY_ZERO_ERROR;
    }

    if (a == INT_MIN && b == -1) {
        return CALC_OVERFLOW_ERROR;
    }

    *output = a / b;
    return CALC_SUCCESS;
}
