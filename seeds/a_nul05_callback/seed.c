/* a_nul05_callback | arm A | class null
 * NULL function pointer check before indirect call */
#include "../common/cisb.h"

typedef int (*cb_t)(int);
int apply(cb_t fn, int x) {
  if (fn == NULL) { cisb_guard_fail(25); return -1; }
  return fn(x);
}

#ifdef SEED_MAIN
int twice(int v) { return 2 * v; }
int main(int argc, char **argv) {
  if (argc != 2) { fprintf(stderr, "usage: %s <1 args>\n", argv[0]); return 2; }
  int twice(int v);
  cb_t fn = arg_is(argv[1], "null") ? NULL : twice;
  printf("ret %d\n", apply(fn, 21));
  return 0;
}
#endif
