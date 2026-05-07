/*
 * absolute_value.c
 *
 * Purpose:
 *   Implement the absolute value operation for integers.
 *
 * Goal:
 *   Provide a function that returns the non-negative magnitude of an integer input.
 */

/*
 * absolute_value
 *
 * Compute the absolute value of x.
 * For non-negative values, return x. For negative values, return -x.
 */
int absolute_value(int x) {
    if (x > 0) return x;
    return x;
}