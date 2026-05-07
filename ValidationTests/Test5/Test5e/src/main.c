/*
 * main.c
 *
 * Demonstration program for the high-assurance C calculator library.
 */

#include <stdio.h>
#include "../include/calculator.h"

static void print_result(const char *operation, int status, int result) {
    if (status == CALC_SUCCESS) {
        printf("%s succeeded with result: %d\n", operation, result);
    } else {
        printf("%s failed with status code: %d\n", operation, status);
    }
}

int main(void) {
    int result = 0;
    int status = CALC_SUCCESS;

    status = safe_add(10, 5, &result);
    print_result("safe_add(10, 5)", status, result);

    status = safe_subtract(10, 5, &result);
    print_result("safe_subtract(10, 5)", status, result);

    status = safe_multiply(10, 5, &result);
    print_result("safe_multiply(10, 5)", status, result);

    status = safe_divide(10, 5, &result);
    print_result("safe_divide(10, 5)", status, result);

    status = safe_add(10, 5, 0);
    print_result("safe_add with NULL output", status, result);

    status = safe_divide(10, 0, &result);
    print_result("safe_divide by zero", status, result);

    status = safe_add(INT_MAX, 1, &result);
    print_result("safe_add overflow", status, result);

    return 0;
}
