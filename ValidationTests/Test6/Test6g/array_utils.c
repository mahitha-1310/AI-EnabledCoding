/*
 * array_utils.c
 *
 * Purpose:
 *   Implement a set of basic array utility functions for Test6g.
 *
 * Goal:
 *   Provide array operations that can be validated through unit tests, including summation, average, maximum, search, and sorting.
 */

#include "array_utils.h"
#include <limits.h>

/*
 * array_sum
 *
 * Return the sum of the first size elements in the array.
 * If arr is NULL or size is not positive, return 0.
 */
int array_sum(const int *arr, int size) {
    if (arr == 0 || size <= 0) {
        return 0;
    }

    int sum = 0;
    for (int i = 0; i < size; i++) {
        sum += arr[i];
    }
    return sum;
}

/*
 * array_average
 *
 * Compute the average value of the first size elements in the array as a double.
 * If arr is NULL or size is not positive, return 0.0.
 */
double array_average(const int *arr, int size) {
    if (arr == 0 || size <= 0) {
        return 0.0;
    }
    return (double)array_sum(arr, size) / size;
}

/*
 * array_max
 *
 * Return the maximum element from the first size values in the array.
 * If arr is NULL or size is not positive, return INT_MIN.
 */
int array_max(const int *arr, int size) {
    if (arr == 0 || size <= 0) {
        return INT_MIN;
    }

    int max_value = arr[0];
    for (int i = 1; i < size; i++) {
        if (arr[i] > max_value) {
            max_value = arr[i];
        }
    }
    return max_value;
}

/*
 * linear_search
 *
 * Search for target in the array and return its index.
 * If arr is NULL or size is not positive, return -1.
 */
int linear_search(const int *arr, int size, int target) {
    if (arr == 0 || size <= 0) {
        return -1;
    }

    for (int i = 0; i < size; i++) {
        if (arr[i] == target) {
            return i;
        }
    }
    return -1;
}

/*
 * bubble_sort
 *
 * Sort the first size elements of the array in ascending order.
 * If arr is NULL or the array is too small to sort, do nothing.
 */
void bubble_sort(int *arr, int size) {
    if (arr == 0 || size <= 1) {
        return;
    }

    for (int i = 0; i < size - 1; i++) {
        for (int j = 0; j < size - i - 1; j++) {
            if (arr[j] > arr[j + 1]) {
                int temp = arr[j];
                arr[j] = arr[j + 1];
                arr[j + 1] = temp;
            }
        }
    }
}
