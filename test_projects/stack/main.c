#include <stdio.h>
#include "stack.h"

int main(void) {
    Stack s;
    stack_init(&s);

    printf("Pushing 10, 20, 30, 40, 50...\n");
    stack_push(&s, 10);
    stack_push(&s, 20);
    stack_push(&s, 30);
    stack_push(&s, 40);
    stack_push(&s, 50);

    stack_display(&s);
    printf("Size: %d\n", stack_size(&s));

    int val;
    stack_peek(&s, &val);
    printf("Peek: %d\n\n", val);

    printf("Popping all elements: ");
    while (!stack_is_empty(&s)) {
        stack_pop(&s, &val);
        printf("%d ", val);
    }
    printf("\n\n");

    printf("Stack is empty: %s\n", stack_is_empty(&s) ? "yes" : "no");
    printf("Pop from empty stack: %s\n",
           stack_pop(&s, &val) == 0 ? "succeeded" : "correctly rejected");

    return 0;
}
