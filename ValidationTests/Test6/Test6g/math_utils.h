/*
 * math_utils.h
 *
 * Purpose:
 *   Declare the math utility functions used by Test6g.
 *
 * Goal:
 *   Provide a clear interface for arithmetic, factorial, gcd, and primality functions.
 */

#ifndef MATH_UTILS_H
#define MATH_UTILS_H

/*
 * add
 *
 * Return the sum of two integers.
 */
int add(int a, int b);

/*
 * subtract
 *
 * Return the result of subtracting b from a.
 */
int subtract(int a, int b);

/*
 * factorial
 *
 * Return n! for non-negative n, otherwise return -1.
 */
int factorial(int n);

/*
 * gcd
 *
 * Return the greatest common divisor of a and b.
 */
int gcd(int a, int b);

/*
 * is_prime
 *
 * Return 1 if n is prime, otherwise return 0.
 */
int is_prime(int n);

#endif
