/* b_ptr03_wrap_ge | arm B | class bounds | ub_by_construction
 * inverted-polarity wrap check: accept only if p + len >= p (UB when it wraps) */
#include "../common/cisb.h"

int range_ok_ge(const char *p, size_t len) {
  if (!(p + len >= p)) { cisb_guard_fail(45); return -1; }
  return 0;
}

#ifdef SEED_MAIN
int main(int argc, char **argv) {
  if (argc != 2) { fprintf(stderr, "usage: %s <1 args>\n", argv[0]); return 2; }
  char *buf = malloc(16);
  printf("ret %d\n", range_ok_ge(buf, arg_ull(argv[1]))); free(buf);
  return 0;
}
#endif
