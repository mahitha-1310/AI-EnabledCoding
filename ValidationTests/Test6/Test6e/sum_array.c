/*
 * sum_array.c
 *
 * Purpose:
 *   Implement array element summation for the Test6e code sample.
 *
 * Goal:
 *   Provide a function that returns the sum of values stored in an integer array.
 */

/*
 * sum_array
 *
 * Compute the sum of the first size elements in arr.
 * The implementation should be verified for correct index handling.
 */
int sum_array(int arr[], int size) {
    int sum = 0;
    for (int i = 0; i < size; i++) {
        sum += arr[i];
    }
    return sum;
}