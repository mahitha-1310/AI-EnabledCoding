#ifndef STACK_H
#define STACK_H

#define STACK_CAPACITY 64

typedef struct {
    int data[STACK_CAPACITY];
    int top;
} Stack;

void stack_init(Stack *s);
int stack_push(Stack *s, int value);
int stack_pop(Stack *s, int *out);
int stack_peek(const Stack *s, int *out);
int stack_is_empty(const Stack *s);
int stack_is_full(const Stack *s);
int stack_size(const Stack *s);
void stack_display(const Stack *s);

#endif
