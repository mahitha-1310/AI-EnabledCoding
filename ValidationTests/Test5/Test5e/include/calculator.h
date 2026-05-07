/*
 * calculator.h
 *
 * Public interface for a high-assurance integer calculator library.
 */

#ifndef CALCULATOR_H
#define CALCULATOR_H

#include <limits.h>

#define CALC_SUCCESS 0
#define CALC_NULL_OUTPUT_ERROR -1
#define CALC_DIVIDE_BY_ZERO_ERROR -2
#define CALC_OVERFLOW_ERROR -3

int safe_add(int a, int b, int *output);
int safe_subtract(int a, int b, int *output);
int safe_multiply(int a, int b, int *output);
int safe_divide(int a, int b, int *output);

#endif
