/*
 * add.h
 *
 * Purpose:
 *   Declare the addition interface for the Test6b implementation.
 *
 * Goal:
 *   Allow unit tests to reference add() without depending on the implementation details.
 */

#ifndef ADD_H
#define ADD_H

/*
 * add
 *
 * Return the sum of two integers.
 */
int add(int a, int b);

#endif