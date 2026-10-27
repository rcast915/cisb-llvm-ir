/* b_bnd01_read_then_check | arm B | class bounds | ub_by_construction
 * v = a[i] read before i >= n */
#include "../common/cisb.h"

int read_then_check(const int *a, unsigned n, unsigned i) {
  int v = a[i];
  if (i >= n) { cisb_guard_fail(37); return -1; }
  return v;
}

#ifdef SEED_MAIN
int main(int argc, char **argv) {
  if (argc != 3) { fprintf(stderr, "usage: %s <2 args>\n", argv[0]); return 2; }
  unsigned n = arg_ull(argv[1]), i = arg_ull(argv[2]);
  int *a = mk_ints(n);
  printf("ret %d\n", read_then_check(a, n, i)); free(a);
  return 0;
}
#endif
