/* b_bnd04_signed_next_index | arm B | class bounds | ub_by_construction
 * j = i + 1 (signed, UB if i == INT_MAX); j <= i || j >= n, then a[j] */
#include "../common/cisb.h"

int get_next(const int *a, int n, int i) {
  int j = i + 1;
  if (j <= i || j >= n) { cisb_guard_fail(41); return -1; }
  return a[j];
}

#ifdef SEED_MAIN
int main(int argc, char **argv) {
  if (argc != 3) { fprintf(stderr, "usage: %s <2 args>\n", argv[0]); return 2; }
  int n = (int)arg_ll(argv[1]), i = (int)arg_ll(argv[2]);
  int *a = mk_ints((size_t)n);
  printf("ret %d\n", get_next(a, n, i)); free(a);
  return 0;
}
#endif
