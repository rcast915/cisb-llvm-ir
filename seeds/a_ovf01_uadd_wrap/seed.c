/* a_ovf01_uadd_wrap | arm A | class overflow
 * unsigned wrap check s = a + b; s < a (defined behaviour) */
#include "../common/cisb.h"

int add_u(unsigned a, unsigned b, unsigned *out) {
  unsigned s = a + b;
  if (s < a) { cisb_guard_fail(11); return -1; }
  *out = s;
  return 0;
}

#ifdef SEED_MAIN
int main(int argc, char **argv) {
  if (argc != 3) { fprintf(stderr, "usage: %s <2 args>\n", argv[0]); return 2; }
  unsigned out = 0; int r = add_u(arg_ull(argv[1]), arg_ull(argv[2]), &out);
  printf("ret %d out=%u\n", r, out);
  return 0;
}
#endif
