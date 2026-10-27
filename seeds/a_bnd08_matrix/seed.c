/* a_bnd08_matrix | arm A | class bounds
 * 2-D bounds r >= rows || c >= cols */
#include "../common/cisb.h"

int mat_get(const int *m, unsigned rows, unsigned cols, unsigned r, unsigned c) {
  if (r >= rows || c >= cols) { cisb_guard_fail(8); return -1; }
  return m[(size_t)r * cols + c];
}

#ifdef SEED_MAIN
int main(int argc, char **argv) {
  if (argc != 5) { fprintf(stderr, "usage: %s <4 args>\n", argv[0]); return 2; }
  unsigned rows = arg_ull(argv[1]), cols = arg_ull(argv[2]), r = arg_ull(argv[3]), c = arg_ull(argv[4]);
  int *m = mk_ints((size_t)rows * cols);
  printf("ret %d\n", mat_get(m, rows, cols, r, c)); free(m);
  return 0;
}
#endif
