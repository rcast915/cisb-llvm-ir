#!/usr/bin/env python3
"""Per-arm summary of results/baseline.csv (arms are never mixed)."""
import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIPES = ["sroa", "sroa+instcombine", "sroa+simplifycfg", "sroa+gvn", "O2", "O3"]


def load(path):
    with open(path) as f:
        return list(csv.DictReader(line for line in f if not line.startswith("#")))


def alive_label(r):
    v = r["alive2_verdict"]
    return v if v != "UNKNOWN" else "UNKNOWN:" + r["alive2_detail"].split(" |", 1)[0]


def main(path=ROOT / "results" / "baseline.csv"):
    rows = load(path)
    out = []
    p = out.append
    for arm in ("A", "B"):
        a = [r for r in rows if r["arm"] == arm]
        seeds = sorted({r["seed"] for r in a})
        p(f"\n=== Arm {arm}: {len(seeds)} seeds x {len(PIPES)} pipelines = {len(a)} rows ===")
        p(f"{'pipeline':17} {'rm':>3} {'wk':>3} {'div':>4} {'div_ub':>6} {'div_noub':>8} {'cand':>4}  alive2 (all rows)")
        for pl in PIPES:
            b = [r for r in a if r["pipeline"] == pl]
            al = Counter(alive_label(r) for r in b)
            p(f"{pl:17} {sum(bool(r['removed_ids']) for r in b):>3} {sum(bool(r['weakened_ids']) for r in b):>3} "
              f"{sum(int(r['divergent_inputs']) > 0 for r in b):>4} {sum(int(r['divergent_ub_attributed']) > 0 for r in b):>6} "
              f"{sum(int(r['divergent_unattributed']) > 0 for r in b):>8} {sum(r['candidate'] == 'True' for r in b):>4}  "
              + ", ".join(f"{k}={v}" for k, v in sorted(al.items())))
        al = Counter(alive_label(r) for r in a)
        p("alive2 verdicts (all rows): " + ", ".join(f"{k}={v}" for k, v in sorted(al.items())))
        cand = [r for r in a if r["candidate"] == "True"]
        p(f"candidates: {len(cand)}; classification: "
          + (", ".join(f"{k}={v}" for k, v in sorted(Counter(r['classification'] for r in cand).items())) or "none"))
        secs = lambda k: sum(float(r[k] or 0) for r in a)
        p(f"time: opt {secs('opt_secs'):.1f}s, alive2 {secs('alive2_secs'):.1f}s (summed over rows)")
        if arm == "A":
            p("Arm A guard removals/weakenings/divergences (candidates):")
            for r in cand:
                p(f"  {r['seed']} {r['pipeline']}: removed={r['removed_ids'] or '-'} weakened={r['weakened_ids'] or '-'} "
                  f"div={r['divergent_inputs']} -> {r['classification']}")
            if not cand:
                p("  none")
        else:
            p("Positive-control gate (Arm B): pipelines that removed (rm) or weakened (wk) the guard")
            for s in seeds:
                hits = [f"{r['pipeline']}({'rm' if r['removed_ids'] else 'wk'})" for r in a
                        if r["seed"] == s and (r["removed_ids"] or r["weakened_ids"])]
                p(f"  {'PASS' if hits else 'NO CHANGE':9} {s:30} {' '.join(hits) or '-'}")
    text = "\n".join(out)
    print(text)
    return text


if __name__ == "__main__":
    t = main(*sys.argv[1:])
    (ROOT / "results" / "baseline_summary.txt").write_text(t + "\n")
