/* Sanitizer smoke test. argv[1]: "clean" | "asan" (heap overflow) | "ubsan" (signed overflow). */
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(int argc, char **argv) {
  const char *mode = argc > 1 ? argv[1] : "clean";
  int *buf = malloc(4 * sizeof(int));
  int idx = strcmp(mode, "asan") == 0 ? 4 : 3;  /* 4 is one past the end */
  buf[idx] = 1;
  int x = strcmp(mode, "ubsan") == 0 ? INT_MAX : 1;
  volatile int y = x + 1;                         /* overflows when x == INT_MAX */
  printf("mode=%s y=%d\n", mode, y);
  free(buf);
  return 0;
}
