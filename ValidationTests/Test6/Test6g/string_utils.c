#include "string_utils.h"
#include <string.h>
#include <ctype.h>

size_t string_length(const char *str) {
    if (str == NULL) {
        return 0;
    }
    return strlen(str);
}

int count_char(const char *str, char target) {
    if (str == NULL) {
        return -1;
    }

    int count = 0;
    for (size_t i = 0; str[i] != '\0'; i++) {
        if (str[i] == target) {
            count++;
        }
    }
    return count;
}

int is_palindrome(const char *str) {
    if (str == NULL) {
        return 0;
    }

    size_t left = 0;
    size_t right = strlen(str);

    if (right == 0) {
        return 1;
    }
    right--;

    while (left < right) {
        while (left < right && !isalnum((unsigned char)str[left])) {
            left++;
        }
        while (left < right && !isalnum((unsigned char)str[right])) {
            right--;
        }
        if (tolower((unsigned char)str[left]) != tolower((unsigned char)str[right])) {
            return 0;
        }
        left++;
        right--;
    }
    return 1;
}

void reverse_string(char *str) {
    if (str == NULL) {
        return;
    }

    size_t left = 0;
    size_t right = strlen(str);

    if (right == 0) {
        return;
    }
    right--;

    while (left < right) {
        char temp = str[left];
        str[left] = str[right];
        str[right] = temp;
        left++;
        right--;
    }
}

int starts_with(const char *str, const char *prefix) {
    if (str == NULL || prefix == NULL) {
        return 0;
    }

    while (*prefix != '\0') {
        if (*str != *prefix) {
            return 0;
        }
        str++;
        prefix++;
    }
    return 1;
}
