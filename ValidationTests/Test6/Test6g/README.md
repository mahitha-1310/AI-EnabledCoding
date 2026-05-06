# C Unit Test Generation Sample Project

This is a small multi-file C project intended for testing unit-test generation tools.

## Files

- `math_utils.c/.h`: arithmetic, factorial, GCD, prime checking
- `string_utils.c/.h`: string length, character counting, palindrome checking, reversing, prefix matching
- `array_utils.c/.h`: sum, average, max, search, sorting
- `temperature.c/.h`: temperature conversions and validation
- `main.c`: simple manual driver

## Build

```bash
gcc -Wall -Wextra -std=c11 main.c math_utils.c string_utils.c array_utils.c temperature.c -o sample_app
./sample_app
```

## Suggested Unit Test Targets

Good edge cases include:

- negative factorial input
- zero and one for prime checking
- NULL strings
- empty strings
- empty arrays
- arrays with negative values
- invalid Celsius values below absolute zero
