/* b_ptr04_wrap_signed_off | arm B | class bounds | ub_by_construction
 * signed offset: reject p + off < p ("moved backwards"); LLVM may fold it to off < 0 */
#include "../common/cisb.h"

int fwd_ok(const char *p, long off) {
  if (p + off < p) { cisb_guard_fail(46); return -1; }
  return (int)p[off];
}

#ifdef SEED_MAIN
int main(int argc, char **argv) {
  if (argc != 2) { fprintf(stderr, "usage: %s <1 args>\n", argv[0]); return 2; }
  char *buf = malloc(16); memset(buf, 'q', 16);
  printf("ret %d\n", fwd_ok(buf, arg_ll(argv[1]))); free(buf);
  return 0;
}
#endif
