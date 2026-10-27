/* a_bnd01_idx_unsigned | arm A | class bounds
 * unsigned index i >= n */
#include "../common/cisb.h"

int get_u(const int *a, unsigned n, unsigned i) {
  if (i >= n) { cisb_guard_fail(1); return -1; }
  return a[i];
}

#ifdef SEED_MAIN
int main(int argc, char **argv) {
  if (argc != 3) { fprintf(stderr, "usage: %s <2 args>\n", argv[0]); return 2; }
  unsigned n = arg_ull(argv[1]), i = arg_ull(argv[2]);
  int *a = mk_ints(n);
  printf("ret %d\n", get_u(a, n, i)); free(a);
  return 0;
}
#endif
