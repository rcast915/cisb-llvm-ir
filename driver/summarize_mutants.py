#!/usr/bin/env python3
"""Per-arm summary of results/mutants.csv + results/mutant_runs.csv (arms never mixed)."""
import csv
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from summarize_baseline import load, alive_label, PIPES, ROOT  # noqa: E402


def main():
    muts = list(csv.DictReader(open(ROOT / "results/mutants.csv")))
    runs = load(ROOT / "results/mutant_runs.csv")
    out = []
    p = out.append
    for arm in ("A", "B"):
        m = [r for r in muts if r["arm"] == arm]
        acc = [r for r in m if r["accepted"] == "True"]
        rr = [r for r in runs if r["arm"] == arm]
        p(f"\n=== Arm {arm} mutants ===")
        p(f"generated {len(m)}; accepted {len(acc)}; rejected: "
          + (", ".join(f"{k}={v}" for k, v in Counter(r['reject_reason'].split(' (')[0] for r in m if r['accepted'] != 'True').items()) or "none"))
        p("by operator (generated/accepted): " + ", ".join(
            f"{op}={sum(r['operator'] == op for r in m)}/{sum(r['operator'] == op for r in acc)}" for op in ("pred_flip", "const_pm1")))
        p("by class (generated/accepted): " + ", ".join(
            f"{c}={sum(r['class'] == c for r in m)}/{sum(r['class'] == c for r in acc)}" for c in ("bounds", "overflow", "null")))
        p(f"pipeline rows: {len(rr)}")
        p(f"{'pipeline':17} {'rm':>3} {'wk':>3} {'div':>4} {'div_ub':>6} {'div_noub':>8} {'cand':>4}  alive2")
        for pl in PIPES:
            b = [r for r in rr if r["pipeline"] == pl]
            al = Counter(alive_label(r) for r in b if r.get("status") == "OK")
            fails = sum(r.get("status") == "OPT_FAIL" for r in b)
            p(f"{pl:17} {sum(bool(r['removed_ids']) for r in b):>3} {sum(bool(r['weakened_ids']) for r in b):>3} "
              f"{sum(int(r['divergent_inputs'] or 0) > 0 for r in b):>4} {sum(int(r['divergent_ub_attributed'] or 0) > 0 for r in b):>6} "
              f"{sum(int(r['divergent_unattributed'] or 0) > 0 for r in b):>8} {sum(r['candidate'] == 'True' for r in b):>4}  "
              + ", ".join(f"{k}={v}" for k, v in sorted(al.items())) + (f", OPT_FAIL={fails}" if fails else ""))
        p("alive2 (all rows): " + ", ".join(f"{k}={v}" for k, v in sorted(Counter(alive_label(r) for r in rr if r.get('status') == 'OK').items())))
        cand = [r for r in rr if r["candidate"] == "True"]
        p(f"candidates: {len(cand)} rows from {len({r['mutant'] for r in cand})} mutants; classification: "
          + (", ".join(f"{k}={v}" for k, v in sorted(Counter(r['classification'] for r in cand).items())) or "none"))
        p(f"time: opt {sum(float(r['opt_secs'] or 0) for r in rr):.1f}s, alive2 {sum(float(r['alive2_secs'] or 0) for r in rr):.1f}s")
        # Unattributed divergences on inputs where the seed's source-level UBSan saw
        # pointer-overflow: the IR UB monitor does not watch pointer arithmetic.
        m2 = {(r["id"], r["input"]): r["observed_reports"] for r in csv.DictReader(open(ROOT / "results/m2_inputs.csv"))}
        un = [r for r in rr if r["divergent_unattributed"] not in ("", "0")]
        gap = [r for r in un if all("ubsan:pointer-overflow" in m2.get((r["seed"], k), "")
                                   for k in __import__("re").findall(r"\bin(\d+) ", r["divergence_detail"]))]
        p(f"unattributed divergences: {len(un)} rows; explained by known monitor gap (seed input has "
          f"source-level ubsan:pointer-overflow): {len(gap)}; unexplained: {len(un) - len(gap)}")
        if arm == "A":
            p("Arm A candidates (each is a potential miscompile lead):")
            for r in cand:
                p(f"  {r['mutant']} {r['pipeline']}: removed={r['removed_ids'] or '-'} weakened={r['weakened_ids'] or '-'} "
                  f"div={r['divergent_inputs']} unattributed={r['divergent_unattributed']} alive2={alive_label(r)} -> {r['classification']}")
            if not cand:
                p("  none")
    text = "\n".join(out)
    print(text)
    (ROOT / "results/mutants_summary.txt").write_text(text + "\n")


if __name__ == "__main__":
    main()
