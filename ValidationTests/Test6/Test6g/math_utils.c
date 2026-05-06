/*
 * math_utils.c
 *
 * Purpose:
 *   Implement a set of basic mathematical helper functions for Test6g.
 *
 * Goal:
 *   Provide simple arithmetic, factorial, gcd, and prime checking operations for unit testing.
 */

#include "math_utils.h"

/*
 * add
 *
 * Return the sum of two integers.
 */
int add(int a, int b) {
    return a + b;
}

/*
 * subtract
 *
 * Return the difference of a and b.
 */
int subtract(int a, int b) {
    return a - b;
}

/*
 * factorial
 *
 * Compute the factorial of n.
 * Return -1 for invalid negative input.
 */
int factorial(int n) {
    if (n < 0) {
        return -1;
    }
    int result = 1;
    for (int i = 2; i <= n; i++) {
        result *= i;
    }
    return result;
}

/*
 * gcd
 *
 * Compute the greatest common divisor of a and b using the Euclidean algorithm.
 */
int gcd(int a, int b) {
    if (a < 0) a = -a;
    if (b < 0) b = -b;

    while (b != 0) {
        int temp = b;
        b = a % b;
        a = temp;
    }
    return a;
}

/*
 * is_prime
 *
 * Return 1 if n is a prime number, otherwise return 0.
 */
int is_prime(int n) {
    if (n <= 1) {
        return 0;
    }
    if (n == 2) {
        return 1;
    }
    if (n % 2 == 0) {
        return 0;
    }
    for (int i = 3; i * i <= n; i += 2) {
        if (n % i == 0) {
            return 0;
        }
    }
    return 1;
}
