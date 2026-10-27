/* a_nul06_out_param | arm A | class null
 * NULL out-parameter check before store */
#include "../common/cisb.h"

int get_answer(int *out) {
  if (out == NULL) { cisb_guard_fail(26); return -22; }
  *out = 42;
  return 0;
}

#ifdef SEED_MAIN
int main(int argc, char **argv) {
  if (argc != 2) { fprintf(stderr, "usage: %s <1 args>\n", argv[0]); return 2; }
  int v = 0; int r = get_answer(arg_is(argv[1], "null") ? NULL : &v);
  printf("ret %d v=%d\n", r, v);
  return 0;
}
#endif
