/* Bounds guard; compiled with -O1 -disable-llvm-passes so opt passes really run. */
int get(const int *a, unsigned n, unsigned i) {
  if (i >= n) return -1;
  return a[i];
}
