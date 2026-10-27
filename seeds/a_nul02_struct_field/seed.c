/* a_nul02_struct_field | arm A | class null
 * !b || !b->data before b->data[0] */
#include "../common/cisb.h"

struct buf { char *data; size_t len; };
int buf_first(const struct buf *b) {
  if (!b || !b->data) { cisb_guard_fail(22); return -1; }
  return (unsigned char)b->data[0];
}

#ifdef SEED_MAIN
int main(int argc, char **argv) {
  if (argc != 2) { fprintf(stderr, "usage: %s <1 args>\n", argv[0]); return 2; }
  struct buf B = { NULL, 0 }; const struct buf *b = &B;
  if (arg_is(argv[1], "null")) b = NULL;
  else if (arg_is(argv[1], "ok")) { B.data = strdup("A"); B.len = 1; }
  printf("ret %d\n", buf_first(b)); free(B.data);
  return 0;
}
#endif
