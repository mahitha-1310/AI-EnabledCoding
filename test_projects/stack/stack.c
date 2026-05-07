#include <stdio.h>
#include "stack.h"

void stack_init(Stack *s) {
    s->top = -1;
}

int stack_push(Stack *s, int value) {
    if (stack_is_full(s))
        return -1;
    s->data[++s->top] = value;
    return 0;
}

int stack_pop(Stack *s, int *out) {
    if (stack_is_empty(s))
        return -1;
    *out = s->data[s->top--];
    return 0;
}

int stack_peek(const Stack *s, int *out) {
    if (stack_is_empty(s))
        return -1;
    *out = s->data[s->top];
    return 0;
}

int stack_is_empty(const Stack *s) {
    return s->top == -1;
}

int stack_is_full(const Stack *s) {
    return s->top == STACK_CAPACITY - 1;
}

int stack_size(const Stack *s) {
    return s->top + 1;
}

void stack_display(const Stack *s) {
    printf("Stack (top -> bottom): ");
    for (int i = s->top; i >= 0; i--)
        printf("%d ", s->data[i]);
    printf("\n");
}
