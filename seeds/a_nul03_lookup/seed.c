/* a_nul03_lookup | arm A | class null
 * result of table lookup checked for NULL */
#include "../common/cisb.h"

struct entry { int key; int val; };
static const struct entry *find(const struct entry *t, unsigned n, int key) {
  for (unsigned i = 0; i < n; i++)
    if (t[i].key == key) return &t[i];
  return NULL;
}
int lookup(const struct entry *t, unsigned n, int key) {
  const struct entry *e = find(t, n, key);
  if (!e) { cisb_guard_fail(23); return -1; }
  return e->val;
}

#ifdef SEED_MAIN
int main(int argc, char **argv) {
  if (argc != 2) { fprintf(stderr, "usage: %s <1 args>\n", argv[0]); return 2; }
  struct entry *t = malloc(3 * sizeof *t);
  for (int k = 0; k < 3; k++) { t[k].key = k + 1; t[k].val = 100 * (k + 1); }
  printf("ret %d\n", lookup(t, 3, (int)arg_ll(argv[1]))); free(t);
  return 0;
}
#endif
