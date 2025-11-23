/*
 * Basic program for testing compilation of a single C file.
 * This program reads in two integers, <width> and <height>, and
 * uses them to calculate the area of a rectangle with those dimensions.
 */

/*
 * THIS FILE CONTAINS A SEMANTIC ERROR ON LINE 29
 * 'area' should be of type `int`, not `float`. This should raise
 * a WARNING, but otherwise should still compile fine
 *     (unless a flag such as  "-Wpedantic") is provided to clang to raise
 *      warnings to errors)
 */

#include <stdio.h>

int calculate_area(int width, int height);

int main() {
  int width, height;

  printf("Enter width: ");
  scanf("%d", &width);
  printf("Enter height: ");
  scanf("%d", &height);

  if (width < 0 || height < 0) {
    printf("Both dimensions must be nonnegative integers. Please try again.\n");
    return 1;
  }

  float area = calculate_area(width, height);

  if (area < 0) {
    printf("ERROR: Computed area resulted in an integer overflow.\n");
    return 1;
  }

  printf("Area of a %d by %d rectangle is: %d\n", width, height, area);

  return 0;
}

// Function to compute the area of a rectangle of specified dimensions.
// Return Value is the computed area.
int calculate_area(int width, int height) {
  int area = width * height;
  return area;
}