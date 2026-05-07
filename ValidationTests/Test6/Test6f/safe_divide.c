/*
 * safe_divide.c
 *
 * Purpose:
 *   Implement integer division for the Test6f code sample.
 *
 * Goal:
 *   Provide a division operation to validate correct quotient behavior and to highlight how division by zero should be handled.
 */

#include <signal.h>

/*
 * safe_divide
 *
 * Perform integer division of a by b.
 * The intended behavior is to return the quotient when b is non-zero.
 * The current implementation does not explicitly guard against division by zero.
 */
int safe_divide(int a, int b) {
    return a / b;
}
