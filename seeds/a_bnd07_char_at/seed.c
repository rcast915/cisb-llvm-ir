/* a_bnd07_char_at | arm A | class bounds
 * string position pos >= len */
#include "../common/cisb.h"

int char_at(const char *s, size_t len, size_t pos) {
  if (pos >= len) { cisb_guard_fail(7); return -1; }
  return (unsigned char)s[pos];
}

#ifdef SEED_MAIN
int main(int argc, char **argv) {
  if (argc != 3) { fprintf(stderr, "usage: %s <2 args>\n", argv[0]); return 2; }
  char *s = strdup(argv[1]); size_t pos = arg_ull(argv[2]);
  printf("ret %d\n", char_at(s, strlen(s), pos)); free(s);
  return 0;
}
#endif
