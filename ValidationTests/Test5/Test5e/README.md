# High-Assurance C Calculator Library

This is a small high-assurance C calculator library designed to test validation pipelines.

## Features

- Safe integer addition, subtraction, multiplication, and division
- Explicit status codes instead of crashes
- NULL output pointer validation
- Division-by-zero validation
- Integer overflow / underflow checks using `INT_MAX` and `INT_MIN`
- Reusable validation helper functions
- Header files with function prototypes and function contracts
- Nested `src/` and `include/` folder structure
- Small `main.c` demo program

## Build Example

```bash
clang -std=c99 -Wall -Wextra -I include src/main.c src/calculator/calculator.c src/validation/validation.c -o calculator_demo
```

## Run Example

```bash
./calculator_demo
```
