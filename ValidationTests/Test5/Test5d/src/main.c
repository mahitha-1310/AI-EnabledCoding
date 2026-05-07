/*
 * main.c
 *
 * Small demo entry point for the calculator.
 * Your metric stage can include this file, but unit testing stages should
 * avoid linking this main() into generated test executables.
 */

#include <stdio.h>
#include "../include/calculator.h"

int main(void) {
    int result = 0;

    if (safe_add(2, 3, &result) == 0) {
        printf("2 + 3 = %d\n", result);
    }

    if (safe_divide(10, 2, &result) == 0) {
        printf("10 / 2 = %d\n", result);
    }

    return 0;
}
