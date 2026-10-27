/* b_bnd02_loop_use_then_check | arm B | class bounds | ub_by_construction
 * loop: s += a[i] before i >= n */
#include "../common/cisb.h"

int sum_then_check(const int *a, unsigned n, unsigned count) {
  int s = 0;
  for (unsigned i = 0; i < count; i++) {
    s += a[i];
    if (i >= n) { cisb_guard_fail(38); return -1; }
  }
  return s;
}

#ifdef SEED_MAIN
int main(int argc, char **argv) {
  if (argc != 3) { fprintf(stderr, "usage: %s <2 args>\n", argv[0]); return 2; }
  unsigned n = arg_ull(argv[1]), count = arg_ull(argv[2]);
  int *a = mk_ints(n);
  printf("ret %d\n", sum_then_check(a, n, count)); free(a);
  return 0;
}
#endif
