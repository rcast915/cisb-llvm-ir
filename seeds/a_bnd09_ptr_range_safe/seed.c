/* a_bnd09_ptr_range_safe | arm A | class bounds
 * UB-free rewrite of b_ptr02: compare len against the remaining space (end - p), never form p + len */
#include "../common/cisb.h"

int copy_region_safe(char *dst, const char *buf, const char *end, size_t off, size_t len) {
  if (off > (size_t)(end - buf)) { cisb_guard_fail(42); return -1; }
  const char *p = buf + off;
  if (len > (size_t)(end - p)) { cisb_guard_fail(43); return -1; }
  memcpy(dst, p, len);
  return 0;
}

#ifdef SEED_MAIN
int main(int argc, char **argv) {
  if (argc != 3) { fprintf(stderr, "usage: %s <2 args>\n", argv[0]); return 2; }
  char *buf = malloc(16), *dst = malloc(16); memset(buf, 'z', 16);
  int r = copy_region_safe(dst, buf, buf + 16, arg_ull(argv[1]), arg_ull(argv[2]));
  printf("ret %d\n", r); free(buf); free(dst);
  return 0;
}
#endif
