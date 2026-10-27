/* b_ovf02_inc_wrap | arm B | class overflow | ub_by_construction
 * signed x + 1 < x */
#include "../common/cisb.h"

int inc_checked(int x) {
  if (x + 1 < x) { cisb_guard_fail(32); return -1; }
  return x + 1;
}

#ifdef SEED_MAIN
int main(int argc, char **argv) {
  if (argc != 2) { fprintf(stderr, "usage: %s <1 args>\n", argv[0]); return 2; }
  printf("ret %d\n", inc_checked((int)arg_ll(argv[1])));
  return 0;
}
#endif
