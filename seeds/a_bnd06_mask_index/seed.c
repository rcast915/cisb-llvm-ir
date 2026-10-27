/* a_bnd06_mask_index | arm A | class bounds
 * power-of-two ring, reject idx with bits outside mask */
#include "../common/cisb.h"

int ring_get(const int *ring, unsigned mask, unsigned idx) {
  if ((idx & mask) != idx) { cisb_guard_fail(6); return -1; }
  return ring[idx];
}

#ifdef SEED_MAIN
int main(int argc, char **argv) {
  if (argc != 3) { fprintf(stderr, "usage: %s <2 args>\n", argv[0]); return 2; }
  unsigned mask = arg_ull(argv[1]), idx = arg_ull(argv[2]);
  int *ring = mk_ints((size_t)mask + 1);
  printf("ret %d\n", ring_get(ring, mask, idx)); free(ring);
  return 0;
}
#endif
