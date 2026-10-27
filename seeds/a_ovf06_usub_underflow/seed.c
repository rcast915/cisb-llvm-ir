/* a_ovf06_usub_underflow | arm A | class overflow
 * unsigned underflow used > total */
#include "../common/cisb.h"

int remaining(size_t total, size_t used, size_t *out) {
  if (used > total) { cisb_guard_fail(16); return -1; }
  *out = total - used;
  return 0;
}

#ifdef SEED_MAIN
int main(int argc, char **argv) {
  if (argc != 3) { fprintf(stderr, "usage: %s <2 args>\n", argv[0]); return 2; }
  size_t out = 0; int r = remaining(arg_ull(argv[1]), arg_ull(argv[2]), &out);
  printf("ret %d out=%zu\n", r, out);
  return 0;
}
#endif
