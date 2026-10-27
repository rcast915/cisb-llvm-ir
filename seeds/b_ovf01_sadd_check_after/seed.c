/* b_ovf01_sadd_check_after | arm B | class overflow | ub_by_construction
 * signed s = a + b computed first, then s < a (UB on overflow) */
#include "../common/cisb.h"

int add_after(int a, int b, int *out) {
  int s = a + b;
  if (b > 0 && s < a) { cisb_guard_fail(31); return -1; }
  *out = s;
  return 0;
}

#ifdef SEED_MAIN
int main(int argc, char **argv) {
  if (argc != 3) { fprintf(stderr, "usage: %s <2 args>\n", argv[0]); return 2; }
  int out = 0; int r = add_after((int)arg_ll(argv[1]), (int)arg_ll(argv[2]), &out);
  printf("ret %d out=%d\n", r, out);
  return 0;
}
#endif
