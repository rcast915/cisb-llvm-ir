/* a_ovf07_signed_len | arm A | class overflow
 * signed length to size_t: len < 0 || len > cap */
#include "../common/cisb.h"

int read_len(char *dst, size_t cap, long len, const char *src) {
  if (len < 0 || (unsigned long)len > cap) { cisb_guard_fail(17); return -1; }
  memcpy(dst, src, (size_t)len);
  return (int)len;
}

#ifdef SEED_MAIN
int main(int argc, char **argv) {
  if (argc != 2) { fprintf(stderr, "usage: %s <1 args>\n", argv[0]); return 2; }
  char *dst = calloc(16, 1), *src = malloc(16); memset(src, 'y', 16);
  printf("ret %d\n", read_len(dst, 16, (long)arg_ll(argv[1]), src)); free(dst); free(src);
  return 0;
}
#endif
