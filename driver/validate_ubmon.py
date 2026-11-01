#!/usr/bin/env python3
"""Validate the IR UB monitor against M2's source-level ASan+UBSan results on unmutated seeds."""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import irub_check  # noqa: E402
from run_baseline import build_plain  # noqa: E402
from check_seeds import ROOT  # noqa: E402

SRC_TO_IR = {"ubsan:signed-integer-overflow": "ubmon:signed", "ubsan:null": "asan:SEGV",
             "ubsan:shift": "ubmon:shl", "asan:heap-buffer-overflow": "asan:heap-buffer-overflow",
             "asan:SEGV": "asan:SEGV"}


def ub_flag(reports):
    return bool(reports)


def main():
    m2 = {(r["id"], int(r["input"])): r for r in csv.DictReader(open(ROOT / "results/m2_inputs.csv"))}
    rows = []
    for sdir in sorted(p for p in (ROOT / "seeds").iterdir() if (p / "inputs.json").exists()):
        meta = json.loads((sdir / "inputs.json").read_text())
        w = ROOT / "work" / "ubmon" / meta["id"]
        w.mkdir(parents=True, exist_ok=True)
        main_o, harness_o = build_plain(meta, w)
        exe, kinds = irub_check.build(w / "seed.ll", w, "seed", main_o, harness_o)
        for k, r in enumerate(irub_check.check(exe, kinds, meta)):
            src = m2[(meta["id"], k)]["observed_reports"].split()
            agree = ub_flag(src) == ub_flag(r["reports"])
            gap = (not agree) and all(s == "ubsan:pointer-overflow" for s in src)
            rows.append({"arm": meta["arm"], "seed": meta["id"], "input": k, "args": " ".join(meta["inputs"][k]["args"]),
                         "source_sanitizers": " ".join(src) or "clean", "ir_monitor": " ".join(r["reports"]) or "clean",
                         "agree_ub_vs_clean": agree, "known_gap_pointer_overflow": gap})
    with open(ROOT / "results/ubmon_validation.csv", "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)
    for arm in "AB":
        a = [r for r in rows if r["arm"] == arm]
        print(f"Arm {arm}: {len(a)} inputs, UB-vs-clean agreement {sum(r['agree_ub_vs_clean'] for r in a)}/{len(a)}, "
              f"disagreements explained by unmonitored pointer-overflow {sum(r['known_gap_pointer_overflow'] for r in a)}")
    for r in rows:
        if not r["agree_ub_vs_clean"]:
            print("  DISAGREE", r["seed"], r["args"], "| source:", r["source_sanitizers"], "| ir:", r["ir_monitor"],
                  "(known gap)" if r["known_gap_pointer_overflow"] else "")


if __name__ == "__main__":
    main()
