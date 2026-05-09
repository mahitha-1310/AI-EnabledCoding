#include <stdio.h>
#include "strutil.h"

int main(void) {
    const char *s = "Hello, World!";

    printf("String: \"%s\"\n", s);
    printf("Length: %d\n", str_len(s));

    int pos = str_find(s, "World");
    printf("\"World\" found at index: %d\n", pos);
    printf("\"xyz\" found at index: %d\n", str_find(s, "xyz"));

    printf("Count of 'l': %d\n\n", str_count_char(s, 'l'));

    char buf[32];
    str_copy(buf, s, sizeof(buf));
    str_reverse(buf);
    printf("Reversed copy: \"%s\"\n\n", buf);

    printf("Compare \"apple\" to \"apple\": %d\n", str_compare("apple", "apple"));
    printf("Compare \"apple\" to \"banana\": %d\n", str_compare("apple", "banana"));
    printf("Compare \"banana\" to \"apple\": %d\n", str_compare("banana", "apple"));

    return 0;
}
