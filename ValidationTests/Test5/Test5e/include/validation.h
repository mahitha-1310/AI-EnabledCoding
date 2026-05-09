/*
 * validation.h
 *
 * Reusable validation helpers for the high-assurance calculator library.
 */

#ifndef VALIDATION_H
#define VALIDATION_H

int is_valid_output_pointer(const int *output);
int is_valid_denominator(int denominator);
int would_add_overflow(int a, int b);
int would_subtract_overflow(int a, int b);
int would_multiply_overflow(int a, int b);

#endif
