#!/usr/bin/env python3
"""M4: mutate every seed (pred_flip, const_pm1), filter, and evaluate like M3.

Per mutant:
  1. static UB filter + `opt -passes=verify` (mutator/mutate.py)
  2. dynamic UB check: mutant IR + ASan + IR UB monitor, -O0, on the seed's inputs
     (driver/irub_check.py). Arm A: any report -> rejected (UB-introducing
     mutant). Arm B: kept; the reports are used for UB attribution only.
  3. the M3 evaluation (driver/run_baseline.evaluate_pipelines): pipelines,
     guard ids before/after, plain-build differential against the mutant's own
     -O0 build, Alive2 (mutant.ll vs optimized mutant), classification.
Outputs: results/mutants.csv (one row per mutant), results/mutant_runs.csv
(one row per accepted mutant x pipeline).
"""
import csv
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mutator"))
import irguards  # noqa: E402
import irub_check  # noqa: E402
import mutate  # noqa: E402
from check_seeds import ROOT, OPT, run, COMMANDS  # noqa: E402
from run_baseline import (build_plain, link_variant, run_inputs, evaluate_pipelines,  # noqa: E402
                          COLUMNS, PRELUDE, ALIVE_SMT_MS)

WORK = ROOT / "work" / "m4"
MUT_COLS = ["arm", "seed", "class", "ub_pattern", "control_role", "mutant", "operator", "function", "line",
            "before", "after", "static_filter", "verify", "dynamic_ub_reports", "accepted", "reject_reason",
            "guard_ids_seed", "guard_ids_mutant", "trip_inputs_seed", "trip_inputs_mutant"]
RUN_COLS = ["mutant", "operator"] + COLUMNS


def process_seed(sdir, mut_rows, run_rows):
    meta = json.loads((sdir / "inputs.json").read_text())
    ws = WORK / meta["id"]
    ws.mkdir(parents=True, exist_ok=True)
    main_o, harness_o = build_plain(meta, ws)
    seed_text = (ws / "seed.ll").read_text()
    seed_ids = irguards.count_ids(seed_text)
    seed_ref = run_inputs(link_variant(ws / "seed.ll", ws, "O0ref", main_o, harness_o), meta)
    for k, (op, fn, line, before, after, text) in enumerate(mutate.mutants(seed_text)):
        mid = f"{meta['id']}__{op}_{k:02d}"
        wm = ws / mid
        wm.mkdir(exist_ok=True)
        mll = wm / "mutant.ll"
        mll.write_text(text)
        mr = {"arm": meta["arm"], "seed": meta["id"], "class": meta["class"], "ub_pattern": meta.get("ub_pattern", ""),
              "control_role": meta.get("control_role", ""), "mutant": mid, "operator": op, "function": fn,
              "line": line, "before": before, "after": after, "guard_ids_seed": " ".join(map(str, seed_ids)),
              "guard_ids_mutant": " ".join(map(str, irguards.count_ids(text))),
              "trip_inputs_seed": sum(bool(r["guards"]) for r in seed_ref)}
        sf = mutate.static_ub_filter(seed_text, text)
        rc, _, err, _ = run([OPT, "-passes=verify", "-disable-output", mll], 60)
        mr.update(static_filter=sf or "ok", verify="ok" if rc == 0 else err.strip()[:120])
        if sf or rc != 0:
            mr.update(accepted=False, reject_reason="static-filter" if sf else "verify")
            mut_rows.append(mr)
            continue
        exe, kinds = irub_check.build(mll, wm, "mutant", main_o, harness_o)
        ub = [r["reports"] for r in irub_check.check(exe, kinds, meta)]
        mr["dynamic_ub_reports"] = " ; ".join(f"in{i}:{'+'.join(r)}" for i, r in enumerate(ub) if r)
        if meta["arm"] == "A" and any(ub):
            mr.update(accepted=False, reject_reason="dynamic-ub (Arm A mutant not UB-free on seed inputs)")
            mut_rows.append(mr)
            continue
        ref = run_inputs(link_variant(mll, wm, "O0ref", main_o, harness_o), meta)
        mr.update(accepted=True, reject_reason="", trip_inputs_mutant=sum(bool(r["guards"]) for r in ref))
        mut_rows.append(mr)
        base = {"mutant": mid, "operator": op, "arm": meta["arm"], "seed": meta["id"], "class": meta["class"],
                "ub_by_construction": meta["ub_by_construction"], "ub_pattern": meta.get("ub_pattern", ""),
                "control_role": meta.get("control_role", "")}
        rows = evaluate_pipelines(meta, mll, wm, ref, ub, main_o, harness_o, base)
        run_rows += rows
        flagged = [r for r in rows if r.get("candidate")]
        print(f"  {mid:46} {before.split('= ')[1]:28} -> {after.split('= ')[1]:28} "
              f"cand={len(flagged)} {' '.join(r['pipeline'] + ':' + r['classification'] for r in flagged)}", flush=True)


def write(path, cols, rows, header=None):
    with open(path, "w", newline="") as f:
        if header:
            f.write(header)
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main():
    seeds = sorted(p for p in (ROOT / "seeds").iterdir() if (p / "inputs.json").exists())
    if sys.argv[1:]:
        seeds = [s for s in seeds if s.name in set(sys.argv[1:])]
    t0 = time.monotonic()
    mut_rows, run_rows = [], []
    for s in seeds:
        print(s.name, flush=True)
        process_seed(s, mut_rows, run_rows)
    write(ROOT / "results/mutants.csv", MUT_COLS, mut_rows)
    write(ROOT / "results/mutant_runs.csv", RUN_COLS, run_rows,
          header=(f"# M4 mutant runs. Operators: {', '.join(mutate.OPERATORS)}. Same pipelines as baseline "
                  f"(prelude '{PRELUDE}' for isolated passes). Reference = the mutant's own plain -O0 build. "
                  "UB attribution = mutant IR + ASan + IR UB monitor at -O0 (never the optimized build). "
                  f"Alive2: alive-tv mutant.ll <pipeline>.ll, --smt-to={ALIVE_SMT_MS}.\n"))
    (ROOT / "results/m4_commands.txt").write_text("\n".join(COMMANDS) + "\n")
    print(f"{len(mut_rows)} mutants, {sum(1 for r in mut_rows if r['accepted'])} accepted, "
          f"{len(run_rows)} pipeline rows in {time.monotonic() - t0:.0f}s")


if __name__ == "__main__":
    main()
