/* a_bnd05_loop_copy | arm A | class bounds
 * in-loop guard i >= dst_len while copying n words */
#include "../common/cisb.h"

int copy_words(int *dst, unsigned dst_len, const int *src, unsigned n) {
  for (unsigned i = 0; i < n; i++) {
    if (i >= dst_len) { cisb_guard_fail(5); return -1; }
    dst[i] = src[i];
  }
  return (int)n;
}

#ifdef SEED_MAIN
int main(int argc, char **argv) {
  if (argc != 3) { fprintf(stderr, "usage: %s <2 args>\n", argv[0]); return 2; }
  unsigned dl = arg_ull(argv[1]), n = arg_ull(argv[2]);
  int *dst = mk_ints(dl), *src = mk_ints(n);
  printf("ret %d\n", copy_words(dst, dl, src, n)); free(dst); free(src);
  return 0;
}
#endif
