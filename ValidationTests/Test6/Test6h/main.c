/*
 * main.c
 *
 * Small driver program used to verify that the sample project compiles
 * as a normal multi-file C program.
 *
 * Your unit testing stage should skip compiling this main() function into
 * the generated unit test executables, because each test file will provide
 * its own main() function.
 */

#include <stdio.h>
#include "math/arithmetic.h"
#include "string_utils/text.h"

int main(void) {
    /*
     * Call functions from source files located in nested folders.
     * This helps verify that folder-based includes work correctly.
     */
    printf("Add: %d\n", add(2, 3));
    printf("Length: %d\n", string_length("hello"));

    return 0;
}
