#!/usr/bin/env bash
# Sanitizer smoke test with the pinned clang: clean run must be silent,
# asan/ubsan runs must each report their bug.
set -uo pipefail
cd "$(dirname "$0")"
source ../../scripts/env.sh
out=$(mktemp -d)
fail=0
tmo 120 "$CLANG" $CLANG_SYSFLAGS -g -O0 -fsanitize=address,undefined -fno-sanitize-recover=undefined \
  san_smoke.c -o "$out/san_smoke" || { echo "compile failed"; exit 1; }
echo "binary links: $(otool -L "$out/san_smoke" | grep -o '[^ ]*clang_rt[^ ]*' | tr '\n' ' ')"
for mode in clean asan ubsan; do
  log=$(tmo 30 "$out/san_smoke" "$mode" 2>&1); rc=$?
  echo "===== san_smoke $mode (exit $rc) ====="
  echo "$log" | grep -E "mode=|ERROR: AddressSanitizer|runtime error|SUMMARY" | sed 's|/.*/validate/m1/||'
  case $mode in
    clean) [ $rc = 0 ] && ! echo "$log" | grep -qE "Sanitizer|runtime error" || fail=1 ;;
    asan)  echo "$log" | grep -q "heap-buffer-overflow" || fail=1 ;;
    ubsan) echo "$log" | grep -q "signed integer overflow" || fail=1 ;;
  esac
done
rm -rf "$out"
[ $fail = 0 ] && echo "SANITIZERS: PASS" || { echo "SANITIZERS: FAIL"; exit 1; }
