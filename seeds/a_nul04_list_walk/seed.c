/* a_nul04_list_walk | arm A | class null
 * walk n && n->val != k, then !n */
#include "../common/cisb.h"

struct node { int val; struct node *next; };
int list_find(const struct node *n, int k) {
  int idx = 0;
  while (n && n->val != k) { n = n->next; idx++; }
  if (!n) { cisb_guard_fail(24); return -1; }
  return idx;
}

#ifdef SEED_MAIN
int main(int argc, char **argv) {
  if (argc != 2) { fprintf(stderr, "usage: %s <1 args>\n", argv[0]); return 2; }
  struct node *h = NULL;
  for (int k = 4; k >= 1; k--) { struct node *x = malloc(sizeof *x); x->val = k; x->next = h; h = x; }
  printf("ret %d\n", list_find(h, (int)arg_ll(argv[1])));
  while (h) { struct node *x = h->next; free(h); h = x; }
  return 0;
}
#endif
