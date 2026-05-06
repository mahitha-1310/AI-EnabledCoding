/*
 * text.h
 *
 * Header file for simple string utility functions.
 * This file is inside a nested folder to test recursive include handling.
 */

#ifndef TEXT_H
#define TEXT_H

/*
 * Returns the length of a null-terminated string.
 * Returns 0 when the input pointer is NULL.
 */
int string_length(const char *text);

/*
 * Returns 1 if the input string is NULL or empty.
 * Returns 0 otherwise.
 */
int is_empty(const char *text);

#endif
