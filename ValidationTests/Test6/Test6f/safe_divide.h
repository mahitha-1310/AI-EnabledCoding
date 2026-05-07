/*
 * safe_divide.h
 *
 * Purpose:
 *   Declare the safe_divide() function for Test6f.
 *
 * Goal:
 *   Provide a clear interface for integer division and document how division-by-zero should be treated.
 */

#ifndef SAFE_DIVIDE_H
#define SAFE_DIVIDE_H

/*
 * safe_divide
 *
 * Divide a by b and return the integer quotient.
 * The implementation should be tested for behavior when b is zero.
 */
int safe_divide(int a, int b);

#endif