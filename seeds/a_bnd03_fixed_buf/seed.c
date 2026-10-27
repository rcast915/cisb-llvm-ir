/* a_bnd03_fixed_buf | arm A | class bounds
 * store into global int[16], idx > 15 */
#include "../common/cisb.h"

int g_buf[16];
int put_fixed(unsigned idx, int v) {
  if (idx > 15) { cisb_guard_fail(3); return -1; }
  g_buf[idx] = v;
  return 0;
}

#ifdef SEED_MAIN
int main(int argc, char **argv) {
  if (argc != 2) { fprintf(stderr, "usage: %s <1 args>\n", argv[0]); return 2; }
  unsigned idx = arg_ull(argv[1]);
  int r = put_fixed(idx, 7);
  printf("ret %d buf0=%d buf15=%d\n", r, g_buf[0], g_buf[15]);
  return 0;
}
#endif
