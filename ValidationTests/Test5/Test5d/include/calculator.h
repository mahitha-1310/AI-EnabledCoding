/*
 * calculator.h
 *
 * Public interface for safe integer calculator operations.
 */

#ifndef CALCULATOR_H
#define CALCULATOR_H

/*
 * Adds two integers and stores the result in output.
 * Returns 0 on success.
 * Returns -1 if output is NULL.
 */
int safe_add(int a, int b, int *output);

/*
 * Subtracts two integers and stores the result in output.
 * Returns 0 on success.
 * Returns -1 if output is NULL.
 */
int safe_subtract(int a, int b, int *output);

/*
 * Multiplies two integers and stores the result in output.
 * Returns 0 on success.
 * Returns -1 if output is NULL.
 */
int safe_multiply(int a, int b, int *output);

/*
 * Divides two integers and stores the result in output.
 * Returns 0 on success.
 * Returns -1 if output is NULL.
 * Returns -2 if division by zero is attempted.
 */
int safe_divide(int a, int b, int *output);

#endif
