#!/usr/bin/env python3
"""Re-check Alive2 UNKNOWN:unsupported-attribute rows after stripping the attributes Alive2 v21 cannot parse.

Run inside the container from /workspace after run_baseline.py / run_mutants.py:
    python3 -I recheck_stripped.py baseline|mutants

For every row whose alive2_verdict is UNKNOWN with an unsupported-attribute sub-label, it removes
`nofree`, `captures(...)` and `nosync` from BOTH the source and the optimized IR (function and
parameter attributes, and attribute groups), then reruns alive-tv with the same flags as the driver.

Interpretation: these attributes are caller-facing promises (the function does not free memory /
does not capture a pointer). Removing them from both sides drops those promises, so a CORRECT result
here shows the optimized *body* refines the source body; it does not validate the inferred attributes
themselves. Report these rows as "CORRECT (attributes stripped)", never as plain CORRECT.
"""
import csv
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path("/workspace")
ALIVE = os.environ["ALIVE_TV"]
STRIP = [r"\bnofree\b", r"\bnosync\b", r"\bcaptures\([^)]*\)"]


def strip(text):
    for pat in STRIP:
        text = re.sub(pat, "", text)
    return re.sub(r"[ \t]{2,}", " ", text)


def alive(src, tgt, meta):
    cmd = [ALIVE, "--smt-to=10000"]
    if meta["loops"]:
        cmd += [f"--src-unroll={meta['alive2_unroll']}", f"--tgt-unroll={meta['alive2_unroll']}"]
    try:
        p = subprocess.run([*cmd, str(src), str(tgt)], capture_output=True, text=True, timeout=300)
        out = p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        return "UNKNOWN:process-timeout", ""
    n = {k: int(m.group(1)) if (m := re.search(rf"(\d+) {k}", out)) else 0
         for k in ("correct transformations", "incorrect transformations", "failed-to-prove transformations", "Alive2 errors")}
    errs = list(dict.fromkeys(re.findall(r"ERROR: (.*)", out)))
    if n["incorrect transformations"]:
        return "INCORRECT", out
    if n["Alive2 errors"] or n["failed-to-prove transformations"]:
        e = " ".join(errs)
        return ("UNKNOWN:smt-timeout" if re.search(r"[Tt]imeout", e) else "UNKNOWN:" + (errs[0][:60] if errs else "ftp")), out
    return ("CORRECT" if n["correct transformations"] else "NO_TRANSFORM"), out


def main(which):
    csv_path = ROOT / "results" / ("baseline.csv" if which == "baseline" else "mutant_runs.csv")
    lines = csv_path.read_text().splitlines(keepends=True)
    rows = list(csv.DictReader(lines[1:]))
    out_rows = []
    for r in rows:
        if not (r["alive2_verdict"] == "UNKNOWN" and "unsupported-attribute" in r["alive2_detail"]):
            continue
        meta = json.loads((ROOT / "seeds" / r["seed"] / "inputs.json").read_text())
        w = ROOT / "work" / ("m3" if which == "baseline" else "m4") / r["seed"]
        if which == "mutants":
            w = w / r["mutant"]
        src = w / ("seed.ll" if which == "baseline" else "mutant.ll")
        tgt = w / f"{r['pipeline']}.ll"
        s2, t2 = w / f"{r['pipeline']}.src.stripped.ll", w / f"{r['pipeline']}.tgt.stripped.ll"
        s2.write_text(strip(src.read_text()))
        t2.write_text(strip(tgt.read_text()))
        verdict, text = alive(s2, t2, meta)
        (w / f"{r['pipeline']}.alive.stripped.txt").write_text(text)
        out_rows.append({"arm": r["arm"], "seed": r["seed"], "mutant": r.get("mutant", ""), "pipeline": r["pipeline"],
                         "candidate": r["candidate"], "classification_before": r["classification"],
                         "alive2_before": r["alive2_detail"].split(" |")[0], "alive2_after_strip": verdict})
        print(f"{r['arm']} {r['seed']:28} {r.get('mutant', ''):44} {r['pipeline']:4} cand={r['candidate']:5} -> {verdict}", flush=True)
    dest = ROOT / "results" / f"{which}_alive2_stripped.csv"
    with open(dest, "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(out_rows[0]) if out_rows else ["seed"])
        wr.writeheader()
        wr.writerows(out_rows)
    from collections import Counter
    print(f"{len(out_rows)} rows re-checked -> {dest.name}:", dict(Counter(r["alive2_after_strip"] for r in out_rows)))


if __name__ == "__main__":
    main(sys.argv[1])
