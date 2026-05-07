/*
 * array_utils.h
 *
 * Purpose:
 *   Declare array utility functions used by Test6g.
 *
 * Goal:
 *   Provide the public interface for common array operations.
 */

#ifndef ARRAY_UTILS_H
#define ARRAY_UTILS_H

/*
 * array_sum
 *
 * Return the sum of the first size elements in arr.
 */
int array_sum(const int *arr, int size);

/*
 * array_average
 *
 * Return the arithmetic average of the first size elements in arr.
 */
double array_average(const int *arr, int size);

/*
 * array_max
 *
 * Return the maximum value among the first size elements in arr.
 */
int array_max(const int *arr, int size);

/*
 * linear_search
 *
 * Search for target in arr and return its zero-based index.
 */
int linear_search(const int *arr, int size, int target);

/*
 * bubble_sort
 *
 * Sort arr using bubble sort in ascending order.
 */
void bubble_sort(int *arr, int size);

#endif
