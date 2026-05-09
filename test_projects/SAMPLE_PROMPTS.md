# Sample Test Projects & Prompts

Each project below can be uploaded to HASAIM via the **Workspace** tab (upload all `.c`, `.h`, and `Makefile` files). Use one of the suggested prompts to drive the AI modernization workflow.

---

## linked_list

A singly-linked list with add, delete, display, and reverse operations.

**Prompt A**
```
Add a `swap` utility function for this linked list implementation.

The `swap` should not swap the data values, but rather the whole nodes in the linked list.

In addition, modify the driver program in `main` to demonstrate the added functionality in action.
```

**Prompt B**
```
Add a `find` function that searches the linked list for a node containing a given integer value
and returns a pointer to that node, or NULL if not found.

Also add a `count` function that returns the number of nodes currently in the list.

Update `main` to demonstrate both new functions.
```

---

## stack

An integer stack backed by a fixed-size array with push, pop, peek, and display.

**Prompt A**
```
Add a `stack_swap` function that swaps the top two elements of the stack without fully
popping and re-pushing them.

Add a `stack_clear` function that empties the stack in a single call.

Update `main` to demonstrate both new functions.
```

**Prompt B**
```
Add a `stack_contains` function that returns 1 if a given value exists anywhere in the stack,
and 0 otherwise. It should not modify the stack.

Also add a `stack_copy` function that copies the entire contents of one stack into another,
leaving the source stack unchanged.

Update `main` to demonstrate both functions.
```

---

## string_utils

A utility library for common C string operations: length, reverse, compare, find, count, and copy.

**Prompt A**
```
Add `str_to_upper` and `str_to_lower` functions that convert all alphabetic characters in a
string to uppercase or lowercase in-place.

Update `main` to demonstrate both functions on several example strings.
```

**Prompt B**
```
Add a `str_trim` function that removes all leading and trailing whitespace characters from
a string in-place.

Also add a `str_starts_with` function that returns 1 if a string begins with a given prefix,
and 0 otherwise.

Update `main` to demonstrate both.
```

---

## circular_buffer

A fixed-capacity FIFO circular buffer with write, read, and display operations.

**Prompt A**
```
Add a `cbuf_peek` function that reads the next value from the buffer without consuming it,
and a `cbuf_flush` function that clears all entries and resets the buffer to its initial state.

Update `main` to demonstrate both functions.
```

**Prompt B**
```
Add a `cbuf_write_overwrite` function that behaves like `cbuf_write` but, when the buffer is
full, overwrites the oldest entry rather than returning an error.

Update `main` to demonstrate the difference between `cbuf_write` (which rejects when full)
and `cbuf_write_overwrite` (which wraps around).
```
