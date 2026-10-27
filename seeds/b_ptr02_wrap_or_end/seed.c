/* b_ptr02_wrap_or_end | arm B | class bounds | ub_by_construction
 * p + len < p || p + len > end, then memcpy */
#include "../common/cisb.h"

int copy_region(char *dst, const char *buf, const char *end, size_t off, size_t len) {
  const char *p = buf + off;
  if (p + len < p || p + len > end) { cisb_guard_fail(34); return -1; }
  memcpy(dst, p, len);
  return 0;
}

#ifdef SEED_MAIN
int main(int argc, char **argv) {
  if (argc != 3) { fprintf(stderr, "usage: %s <2 args>\n", argv[0]); return 2; }
  char *buf = malloc(16), *dst = malloc(16); memset(buf, 'z', 16);
  int r = copy_region(dst, buf, buf + 16, arg_ull(argv[1]), arg_ull(argv[2]));
  printf("ret %d\n", r); free(buf); free(dst);
  return 0;
}
#endif
