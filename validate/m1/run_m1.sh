#!/usr/bin/env bash
# M1 self-test: alive-tv must verify good.ll and ub_legal.ll and reject bad.ll.
set -uo pipefail
cd "$(dirname "$0")"
source ../../scripts/env.sh
fail=0
check() {  # file expected(correct|incorrect)
  out=$(tmo 60 "$ALIVE_TV" --smt-to=20000 "$1" 2>&1); rc=$?
  echo "===== alive-tv $1 (exit $rc) ====="; echo "$out"
  if [ "$2" = correct ];   then echo "$out" | grep -q "Transformation seems to be correct" || fail=1; fi
  if [ "$2" = incorrect ]; then echo "$out" | grep -q "Transformation doesn't verify"     || fail=1; fi
}
check good.ll correct
check bad.ll incorrect
check ub_legal.ll correct
# Also confirm opt actually performs the nsw fold on the real pass.
echo "===== opt -passes=instcombine ub_legal src ====="
sed -n '/@src/,/^}/p' ub_legal.ll | tmo 60 "$OPT" -S -passes=instcombine - || fail=1
# Round trip: clang-23 IR -> opt instcombine -> alive-tv before.ll after.ll (2-file mode).
t=$(mktemp -d)
tmo 60 "$CLANG" $CLANG_SYSFLAGS $CLANG_IRFLAGS roundtrip.c -o "$t/before.ll" || fail=1
grep -q optnone "$t/before.ll" && { echo "before.ll has optnone"; fail=1; }
tmo 60 "$OPT" -S -passes='sroa,instcombine' "$t/before.ll" -o "$t/after.ll" || fail=1
out=$(tmo 120 "$ALIVE_TV" --smt-to=20000 "$t/before.ll" "$t/after.ll" 2>&1); rc=$?
echo "===== alive-tv roundtrip before.ll after.ll (exit $rc) ====="; echo "$out" | sed -n '/=>/,$p'
echo "$out" | grep -q "Transformation seems to be correct" || fail=1
rm -rf "$t"
[ $fail = 0 ] && echo "M1: PASS" || { echo "M1: FAIL"; exit 1; }
