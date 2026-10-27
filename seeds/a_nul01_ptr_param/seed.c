/* a_nul01_ptr_param | arm A | class null
 * if (!p) before *p */
#include "../common/cisb.h"

int read_val(const int *p) {
  if (!p) { cisb_guard_fail(21); return -1; }
  return *p;
}

#ifdef SEED_MAIN
int main(int argc, char **argv) {
  if (argc != 2) { fprintf(stderr, "usage: %s <1 args>\n", argv[0]); return 2; }
  int *p = arg_is(argv[1], "null") ? NULL : mk_ints(1);
  printf("ret %d\n", read_val(p)); free(p);
  return 0;
}
#endif
