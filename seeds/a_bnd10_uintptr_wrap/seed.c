/* a_bnd10_uintptr_wrap | arm A | class bounds
 * UB-free rewrite of b_ptr01: do the wrap test on uintptr_t (unsigned, defined), not on char * */
#include "../common/cisb.h"

int range_ok_uintptr(const char *p, size_t len) {
  uintptr_t a = (uintptr_t)p;
  if (a + len < a) { cisb_guard_fail(44); return -1; }
  return 0;
}

#ifdef SEED_MAIN
int main(int argc, char **argv) {
  if (argc != 2) { fprintf(stderr, "usage: %s <1 args>\n", argv[0]); return 2; }
  char *buf = malloc(16);
  printf("ret %d\n", range_ok_uintptr(buf, arg_ull(argv[1]))); free(buf);
  return 0;
}
#endif
