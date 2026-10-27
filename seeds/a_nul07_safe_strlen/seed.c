/* a_nul07_safe_strlen | arm A | class null
 * NULL string check before length loop */
#include "../common/cisb.h"

size_t safe_len(const char *s) {
  if (!s) { cisb_guard_fail(27); return 0; }
  size_t n = 0;
  while (s[n]) n++;
  return n;
}

#ifdef SEED_MAIN
int main(int argc, char **argv) {
  if (argc != 2) { fprintf(stderr, "usage: %s <1 args>\n", argv[0]); return 2; }
  char *s = arg_is(argv[1], "null") ? NULL : strdup(argv[1]);
  printf("ret %zu\n", safe_len(s)); free(s);
  return 0;
}
#endif
