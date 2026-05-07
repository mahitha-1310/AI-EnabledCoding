/*
 * validation.c
 *
 * Implements small reusable validation helpers for the calculator.
 */

#include "../../include/validation.h"

int is_valid_output_pointer(const int *output) {
    /*
     * A valid output pointer must not be NULL.
     */
    return output != 0;
}

int is_valid_denominator(int denominator) {
    /*
     * Division by zero is invalid.
     */
    return denominator != 0;
}
