/* a_bnd04_memcpy_range | arm A | class bounds
 * overflow-safe range check off > cap || len > cap - off before memcpy */
#include "../common/cisb.h"

int copy_in(char *dst, size_t cap, size_t off, const char *src, size_t len) {
  if (off > cap || len > cap - off) { cisb_guard_fail(4); return -1; }
  memcpy(dst + off, src, len);
  return 0;
}

#ifdef SEED_MAIN
int main(int argc, char **argv) {
  if (argc != 4) { fprintf(stderr, "usage: %s <3 args>\n", argv[0]); return 2; }
  size_t cap = arg_ull(argv[1]), off = arg_ull(argv[2]), len = arg_ull(argv[3]);
  char *dst = calloc(cap, 1), *src = malloc(cap);
  memset(src, 'x', cap);
  int r = copy_in(dst, cap, off, src, len);
  printf("ret %d last=%d\n", r, cap ? dst[cap - 1] : 0); free(dst); free(src);
  return 0;
}
#endif
