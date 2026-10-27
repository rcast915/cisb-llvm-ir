/* b_nul01_deref_then_check | arm B | class null | ub_by_construction
 * d->flags read before if (!d) (tun.c pattern) */
#include "../common/cisb.h"

struct dev { int flags; };
int dev_poll(struct dev *d) {
  int f = d->flags;
  if (!d) { cisb_guard_fail(35); return -1; }
  return f;
}

#ifdef SEED_MAIN
int main(int argc, char **argv) {
  if (argc != 2) { fprintf(stderr, "usage: %s <1 args>\n", argv[0]); return 2; }
  struct dev D = { 5 };
  printf("ret %d\n", dev_poll(arg_is(argv[1], "null") ? NULL : &D));
  return 0;
}
#endif
