/* b_nul02_store_then_check | arm B | class null | ub_by_construction
 * *out = v before if (out == NULL) */
#include "../common/cisb.h"

int store_then_check(int *out, int v) {
  *out = v;
  if (out == NULL) { cisb_guard_fail(36); return -22; }
  return 0;
}

#ifdef SEED_MAIN
int main(int argc, char **argv) {
  if (argc != 2) { fprintf(stderr, "usage: %s <1 args>\n", argv[0]); return 2; }
  int v = 0; int r = store_then_check(arg_is(argv[1], "null") ? NULL : &v, 9);
  printf("ret %d v=%d\n", r, v);
  return 0;
}
#endif
