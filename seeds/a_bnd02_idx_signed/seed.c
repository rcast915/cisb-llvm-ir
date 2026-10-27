/* a_bnd02_idx_signed | arm A | class bounds
 * signed index i < 0 || i >= n (compound guard) */
#include "../common/cisb.h"

int get_s(const int *a, int n, int i) {
  if (i < 0 || i >= n) { cisb_guard_fail(2); return -1; }
  return a[i];
}

#ifdef SEED_MAIN
int main(int argc, char **argv) {
  if (argc != 3) { fprintf(stderr, "usage: %s <2 args>\n", argv[0]); return 2; }
  int n = (int)arg_ll(argv[1]), i = (int)arg_ll(argv[2]);
  int *a = mk_ints((size_t)n);
  printf("ret %d\n", get_s(a, n, i)); free(a);
  return 0;
}
#endif
