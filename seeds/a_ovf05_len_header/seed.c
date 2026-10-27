/* a_ovf05_len_header | arm A | class overflow
 * len + HDR fits in uint32: len > UINT32_MAX - HDR */
#include "../common/cisb.h"

#define HDR 16u
int frame_size(uint32_t len, uint32_t *out) {
  if (len > UINT32_MAX - HDR) { cisb_guard_fail(15); return -1; }
  *out = len + HDR;
  return 0;
}

#ifdef SEED_MAIN
int main(int argc, char **argv) {
  if (argc != 2) { fprintf(stderr, "usage: %s <1 args>\n", argv[0]); return 2; }
  uint32_t out = 0; int r = frame_size((uint32_t)arg_ull(argv[1]), &out);
  printf("ret %d out=%u\n", r, out);
  return 0;
}
#endif
