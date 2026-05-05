// C Program to use code another
// file into this file
#include "second.h"
#include <stdio.h>

int main() {
  // declared two variables
  int a = 4, b = 5;

  // sum function called
  int ans = sum(a, b);
  printf("Sum: %d\n", ans);

  // sub function called
  ans = sub(a, b);
  printf("Subtraction: %d\n", ans);

  // multiply function called
  ans = multiply(a, b);
  printf("Multiply: %d\n", ans);

  return 0;
}