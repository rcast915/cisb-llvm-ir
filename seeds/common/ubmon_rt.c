/* Runtime for driver/ubmon.py: report a UB site and continue (like UBSan recover mode). */
#include <stdio.h>
void cisb_ub(_Bool is_ub, int site) {
  if (is_ub) { fprintf(stderr, "UBMON: site %d\n", site); fflush(stderr); }
}
