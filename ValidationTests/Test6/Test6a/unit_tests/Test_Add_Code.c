#include <assert.h>
#include <stdio.h>
#include "add.h"

// Include the function under test
// #include "add.c"

void test_positive() {
    assert(add(2, 3) == 5);
}

void test_negative() {
    assert(add(-1, -1) == -2);
}

void test_false_positive() {
    // This test is supposed to pass
    assert(add(1, 1) != 3);
}

void test_failure() {
    // This test is expected to fail
    assert(add(2, 2) == 5);
}

int main() {
    printf("Running test_positive...\n");
    test_positive();

    printf("Running test_negative...\n");
    test_negative();

    printf("Running test_false_positive...\n");
    test_false_positive();

    //printf("Running test_failure...\n");
    //test_failure();  // This will trigger assertion failure

    printf("All tests passed.\n");
    return 0;
}
