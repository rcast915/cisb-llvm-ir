/* b_bnd03_signed_range_end | arm B | class bounds | ub_by_construction
 * range check end = off + len (signed, UB on overflow); end < off || end > cap */
#include "../common/cisb.h"

int range_end(int off, int len, int cap) {
  if (len < 0) { cisb_guard_fail(39); return -1; }
  int end = off + len;
  if (end < off || end > cap) { cisb_guard_fail(40); return -1; }
  return end;
}

#ifdef SEED_MAIN
int main(int argc, char **argv) {
  if (argc != 4) { fprintf(stderr, "usage: %s <3 args>\n", argv[0]); return 2; }
  printf("ret %d\n", range_end((int)arg_ll(argv[1]), (int)arg_ll(argv[2]), (int)arg_ll(argv[3])));
  return 0;
}
#endif
