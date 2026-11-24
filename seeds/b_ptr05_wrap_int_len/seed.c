/* b_ptr05_wrap_int_len | arm B | class bounds | ub_by_construction
 * 32-bit signed length: p + len < p || p + len > end (negative len moves p backwards: UB) */
#include "../common/cisb.h"

int read_last(const char *buf, const char *end, int len) {
  if (buf + len < buf || buf + len > end) { cisb_guard_fail(47); return -1; }
  return len ? (int)buf[len - 1] : 0;
}

#ifdef SEED_MAIN
int main(int argc, char **argv) {
  if (argc != 2) { fprintf(stderr, "usage: %s <1 args>\n", argv[0]); return 2; }
  char *buf = malloc(16); memset(buf, 'r', 16);
  printf("ret %d\n", read_last(buf, buf + 16, (int)arg_ll(argv[1]))); free(buf);
  return 0;
}
#endif
