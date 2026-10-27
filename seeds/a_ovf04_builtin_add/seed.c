/* a_ovf04_builtin_add | arm A | class overflow
 * __builtin_add_overflow (llvm.sadd.with.overflow) */
#include "../common/cisb.h"

int add_checked(int a, int b, int *out) {
  int r;
  if (__builtin_add_overflow(a, b, &r)) { cisb_guard_fail(14); return -1; }
  *out = r;
  return 0;
}

#ifdef SEED_MAIN
int main(int argc, char **argv) {
  if (argc != 3) { fprintf(stderr, "usage: %s <2 args>\n", argv[0]); return 2; }
  int out = 0; int r = add_checked((int)arg_ll(argv[1]), (int)arg_ll(argv[2]), &out);
  printf("ret %d out=%d\n", r, out);
  return 0;
}
#endif
