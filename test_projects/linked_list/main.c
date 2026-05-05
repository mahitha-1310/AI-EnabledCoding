#include <stdio.h>
#include <stdlib.h>
#include "linkedlist.h"

int main(void) {
  List *list = makelist();
  add(1, list);
  add(20, list);
  add(2, list);
  add(5, list);
  add(8, list);
  add(9, list);
  add(13, list);

  printf("Linked list:\n");
  display(list);
  printf("End list.\n\n");

  delete(2, list);
  printf("\"Delete(2, list)\"\n");
  printf("Linked list:\n");
  display(list);
  printf("End list.\n\n");

  delete(1, list);
  printf("\"Delete(1, list)\"\n");
  printf("Linked list:\n");
  display(list);
  printf("End list.\n\n");

  delete(20, list);
  printf("\"Delete(20, list)\"\n");
  printf("Linked list:\n");
  display(list);
  printf("End list.\n\n");

  reverse(list);
  printf("Reversed: using three pointers. \n");
  printf("Linked list:\n");
  display(list);
  printf("End list.\n\n");

  reverse_using_two_pointers(list);
  printf("Reversed: using two pointers. \n");
  printf("Linked list:\n");
  display(list);
  printf("End list.\n\n");
  destroy(list);
  return 0;
}
