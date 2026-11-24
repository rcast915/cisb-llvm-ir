#!/usr/bin/env python3
"""Row-by-row comparison of two result CSVs (e.g. macOS vs Linux). Usage: compare_runs.py A.csv B.csv"""
import csv, sys
def load(p):
    L = open(p, encoding="utf-8").read().splitlines()[1:]
    return {(r["seed"], r.get("mutant", ""), r["pipeline"]): r for r in csv.DictReader(L)}
a, b = load(sys.argv[1]), load(sys.argv[2])
print(f"rows: {len(a)} vs {len(b)}; only in A: {len(a.keys()-b.keys())}; only in B: {len(b.keys()-a.keys())}")
keys = ["guard_ids_after", "removed_ids", "weakened_ids", "divergent_inputs", "candidate", "alive2_verdict", "classification"]
same = 0
for k in sorted(a.keys() & b.keys()):
    d = [f"{f}: {a[k][f]!r} -> {b[k][f]!r}" for f in keys if a[k][f] != b[k][f]]
    if d:
        print(" ", "/".join(x for x in k if x), "|", "; ".join(d), "| secs", a[k]["alive2_secs"], "->", b[k]["alive2_secs"])
    else:
        same += 1
print(f"identical on {', '.join(keys)}: {same}")
