/* a_ovf02_sadd_precheck | arm A | class overflow
 * signed add pre-check against INT_MAX - b / INT_MIN - b */
#include "../common/cisb.h"

int add_s(int a, int b, int *out) {
  if ((b > 0 && a > INT_MAX - b) || (b < 0 && a < INT_MIN - b)) { cisb_guard_fail(12); return -1; }
  *out = a + b;
  return 0;
}

#ifdef SEED_MAIN
int main(int argc, char **argv) {
  if (argc != 3) { fprintf(stderr, "usage: %s <2 args>\n", argv[0]); return 2; }
  int out = 0; int r = add_s((int)arg_ll(argv[1]), (int)arg_ll(argv[2]), &out);
  printf("ret %d out=%d\n", r, out);
  return 0;
}
#endif
