/* a_ovf03_mul_alloc | arm A | class overflow
 * calloc-style n * sz overflow check n > SIZE_MAX / sz */
#include "../common/cisb.h"

void *alloc_array(size_t n, size_t sz) {
  if (sz != 0 && n > SIZE_MAX / sz) { cisb_guard_fail(13); return NULL; }
  return malloc(n * sz);
}

#ifdef SEED_MAIN
int main(int argc, char **argv) {
  if (argc != 3) { fprintf(stderr, "usage: %s <2 args>\n", argv[0]); return 2; }
  void *p = alloc_array(arg_ull(argv[1]), arg_ull(argv[2]));
  printf("ret %s\n", p ? "ok" : "null"); free(p);
  return 0;
}
#endif
