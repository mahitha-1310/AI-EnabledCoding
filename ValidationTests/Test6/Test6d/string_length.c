/*
 * string_length.c
 *
 * Purpose:
 *   Implement a string length calculation for the Test6d code sample.
 *
 * Goal:
 *   Provide a simple function that returns the length of a C string.
 */

/*
 * string_length
 *
 * Return the number of characters in the input string, not including the null terminator.
 */
int string_length(const char *s) {
    int len = 0;
    while (s[len] != '\0') {
        len++;
    }
    return len;
}