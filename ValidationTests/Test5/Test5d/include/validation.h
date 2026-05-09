/*
 * validation.h
 *
 * Public interface for reusable validation helpers.
 */

#ifndef VALIDATION_H
#define VALIDATION_H

/*
 * Returns 1 if the pointer is not NULL.
 * Returns 0 otherwise.
 */
int is_valid_output_pointer(const int *output);

/*
 * Returns 1 if the denominator is safe for division.
 * Returns 0 if the denominator is zero.
 */
int is_valid_denominator(int denominator);

#endif
