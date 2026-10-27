/* a_ovf08_shift_amount | arm A | class overflow
 * shift amount s >= 32 */
#include "../common/cisb.h"

int shl_checked(unsigned x, unsigned s, unsigned *out) {
  if (s >= 32) { cisb_guard_fail(18); return -1; }
  *out = x << s;
  return 0;
}

#ifdef SEED_MAIN
int main(int argc, char **argv) {
  if (argc != 3) { fprintf(stderr, "usage: %s <2 args>\n", argv[0]); return 2; }
  unsigned out = 0; int r = shl_checked(arg_ull(argv[1]), arg_ull(argv[2]), &out);
  printf("ret %d out=%u\n", r, out);
  return 0;
}
#endif
