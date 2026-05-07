#ifndef STRING_UTILS_H
#define STRING_UTILS_H

#include <stddef.h>

size_t string_length(const char *str);
int count_char(const char *str, char target);
int is_palindrome(const char *str);
void reverse_string(char *str);
int starts_with(const char *str, const char *prefix);

#endif
