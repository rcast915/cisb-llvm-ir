/* Shared seed support.
 * Every guard's failing side calls cisb_guard_fail(<unique id>). It is defined
 * in harness.c, outside the seed's IR, so passes cannot see through it: the
 * call is the error-path marker used to count guards in IR and to observe a
 * guard trip at run time ("GUARD <id>" on stdout).
 * main() and its helpers are only compiled with -DSEED_MAIN, so the seed IR
 * contains just the guarded function(s). */
#ifndef CISB_H
#define CISB_H
#include <limits.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>

void cisb_guard_fail(int id);

#ifdef SEED_MAIN
#include <stdio.h>
static long long arg_ll(const char *s) { return strtoll(s, NULL, 0); }
static unsigned long long arg_ull(const char *s) { return strtoull(s, NULL, 0); }
static int arg_is(const char *s, const char *word) { return strcmp(s, word) == 0; }
/* Heap array of exactly n ints (so ASan sees the real bounds); a[k] = 10k + 1. */
static int *mk_ints(size_t n) {
  int *a = malloc(n ? n * sizeof(int) : 1);
  for (size_t k = 0; k < n; k++) a[k] = (int)(10 * k + 1);
  return a;
}
#endif
#endif
