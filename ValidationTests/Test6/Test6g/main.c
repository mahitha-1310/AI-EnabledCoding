#include <stdio.h>
#include "math_utils.h"
#include "string_utils.h"
#include "array_utils.h"
#include "temperature.h"

int main(void) {
    int numbers[] = {5, 2, 9, 1, 3};
    char word[] = "level";

    printf("add(2, 3) = %d\n", add(2, 3));
    printf("factorial(5) = %d\n", factorial(5));
    printf("is_prime(17) = %d\n", is_prime(17));

    printf("string_length(level) = %zu\n", string_length(word));
    printf("is_palindrome(level) = %d\n", is_palindrome(word));

    printf("array_sum = %d\n", array_sum(numbers, 5));
    printf("array_max = %d\n", array_max(numbers, 5));

    printf("0C to F = %.2f\n", celsius_to_fahrenheit(0.0));
    printf("100C to K = %.2f\n", celsius_to_kelvin(100.0));

    return 0;
}
