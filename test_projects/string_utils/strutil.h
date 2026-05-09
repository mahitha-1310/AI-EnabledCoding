#ifndef STRUTIL_H
#define STRUTIL_H

#include <stddef.h>

int str_len(const char *s);
void str_reverse(char *s);
int str_compare(const char *a, const char *b);
int str_find(const char *haystack, const char *needle);
int str_count_char(const char *s, char c);
void str_copy(char *dst, const char *src, size_t n);

#endif
