#!/usr/bin/env python3
"""M2 seed acceptance check. Run via scripts/check_seeds.sh (needs scripts/env.sh).

Per seed:
  1. Emit IR with $CLANG_IRFLAGS (no main), `opt -passes=verify`, and check that
     no defined function carries `optnone`.
  2. Count guards in the IR (driver/irguards.py); every id in inputs.json
     guard_ids must be present and conditional.
  3. Build -O0 with ASan+UBSan (+ main + harness) and run every input.
     Arm A: every input must be sanitizer-clean, exit 0, and print GUARD iff the
            input is a "trip" input.
     Arm B: observed sanitizer reports (ordered, de-duplicated kinds) and GUARD
            output must equal the recorded expectation.
Writes results/m2_seeds.csv, results/m2_inputs.csv, results/m2_commands.txt.
"""
import csv
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "driver"))
import irguards  # noqa: E402

CLANG, OPT = os.environ["CLANG"], os.environ["OPT"]
SYS = shlex.split(os.environ["CLANG_SYSFLAGS"])
IRFLAGS = shlex.split(os.environ["CLANG_IRFLAGS"])
SANFLAGS = ["-O0", "-g", "-fsanitize=address,undefined"]
RUN_ENV = dict(os.environ, ASAN_OPTIONS="detect_leaks=0:abort_on_error=0",
               UBSAN_OPTIONS="print_stacktrace=0:halt_on_error=0")
WORK = ROOT / "work" / "m2"
COMMANDS = []

UBSAN_KINDS = [
    (r"signed integer overflow", "ubsan:signed-integer-overflow"),
    (r"pointer index expression .* overflowed|offset to .* overflowed|applying non-zero offset", "ubsan:pointer-overflow"),
    (r"null pointer", "ubsan:null"),
    (r"shift exponent|left shift of", "ubsan:shift"),
    (r"out of bounds for type", "ubsan:bounds"),
]


def run(cmd, timeout, log=True, **kw):
    if log:
        COMMANDS.append(" ".join(shlex.quote(str(c)) for c in cmd))
    t0 = time.monotonic()
    try:
        p = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, timeout=timeout, **kw)
        return p.returncode, p.stdout, p.stderr, time.monotonic() - t0
    except subprocess.TimeoutExpired as e:
        return "TIMEOUT", e.stdout or "", e.stderr or "", time.monotonic() - t0


def report_kinds(stderr):
    kinds = []
    for ln in stderr.splitlines():
        k = None
        m = re.search(r"ERROR: AddressSanitizer: ([\w-]+)", ln)
        if m:
            k = "asan:" + m.group(1)
        elif "runtime error:" in ln:
            msg = ln.split("runtime error:", 1)[1]
            k = next((kind for pat, kind in UBSAN_KINDS if re.search(pat, msg)), "ubsan:other")
        if k and (not kinds or kinds[-1] != k):
            kinds.append(k)
    return kinds


def has_optnone(ll_text):
    groups = dict(re.findall(r"^attributes (#\d+) = \{(.*)\}", ll_text, re.M))
    bad = []
    for m in re.finditer(r"^define\b.*?@([\w.$]+)\(.*\)(.*)\{", ll_text, re.M):
        attrs = m.group(2)
        refs = re.findall(r"#\d+", attrs)
        if "optnone" in attrs or any("optnone" in groups.get(r, "") for r in refs):
            bad.append(m.group(1))
    return bad


def check_seed(sdir):
    meta = json.loads((sdir / "inputs.json").read_text())
    w = WORK / meta["id"]
    w.mkdir(parents=True, exist_ok=True)
    seed_c, ll, exe = sdir / "seed.c", w / "seed.ll", w / "seed_san"
    row = {k: meta.get(k, "") for k in ("id", "arm", "class", "ub_pattern", "loops", "alive2_unroll")}
    row["ub_by_construction"] = meta["ub_by_construction"]
    problems = []

    rc, _, err, _ = run([CLANG, *SYS, *IRFLAGS, seed_c, "-o", ll], 60)
    row["ir_ok"] = rc == 0
    if rc != 0:
        problems.append("ir-compile: " + err.strip().splitlines()[-1])
    else:
        rc, _, err, _ = run([OPT, "-passes=verify", "-disable-output", ll], 60)
        row["verify_ok"] = rc == 0
        if rc != 0:
            problems.append("verify: " + err.strip())
        text = ll.read_text()
        defined = re.findall(r"^define\b.*?@([\w.$]+)\(", text, re.M)
        row["defined_functions"] = " ".join(defined)
        on = has_optnone(text)
        row["optnone_functions"] = " ".join(on)
        if on:
            problems.append("optnone on " + ",".join(on))
        missing = [f for f in meta["functions"] if f not in defined]
        if missing:
            problems.append("missing functions " + ",".join(missing))
        ids = irguards.count_ids(text)
        row["guards_in_ir"] = len(ids)
        row["guard_ids_ir"] = " ".join(map(str, ids))
        if sorted(meta["guard_ids"]) != ids:
            problems.append(f"guard ids {ids} != expected {meta['guard_ids']}")

    rc, _, err, _ = run([CLANG, *SYS, *SANFLAGS, "-DSEED_MAIN", seed_c, ROOT / "seeds/common/harness.c", "-o", exe], 120)
    row["san_build_ok"] = rc == 0
    in_rows = []
    if rc != 0:
        problems.append("san-build: " + err.strip().splitlines()[-1])
    else:
        for k, inp in enumerate(meta["inputs"]):
            rc, out, err, dt = run([exe, *inp["args"]], 10, env=RUN_ENV)
            kinds = report_kinds(err)
            guard_lines = re.findall(r"^GUARD (\d+)$", out, re.M)
            exp_guard = inp["expect_guard_output"]
            ok = (bool(guard_lines) == exp_guard
                  and all(int(g) in meta["guard_ids"] for g in guard_lines)
                  and kinds == inp["expect_reports"])
            if meta["arm"] == "A":
                ok = ok and rc == 0 and not kinds
            in_rows.append({"id": meta["id"], "arm": meta["arm"], "class": meta["class"],
                            "input": k, "args": " ".join(inp["args"]), "guard": inp["guard"],
                            "expect_guard_output": exp_guard, "observed_guard": " ".join(guard_lines),
                            "expect_reports": " ".join(inp["expect_reports"]),
                            "observed_reports": " ".join(kinds), "exit": rc,
                            "stdout": out.strip().replace("\n", " | "),
                            "secs": f"{dt:.2f}", "ok": ok})
            if not ok:
                problems.append(f"input {k} {inp['args']}: exit={rc} guard={guard_lines} reports={kinds}")
    row["inputs"] = len(in_rows)
    row["trip_inputs"] = sum(1 for r in in_rows if r["guard"] == "trip")
    row["inputs_ok"] = sum(1 for r in in_rows if r["ok"])
    row["status"] = "OK" if not problems else "FAIL"
    row["problems"] = "; ".join(problems)
    return row, in_rows


def main():
    seeds = sorted(p for p in (ROOT / "seeds").iterdir() if (p / "inputs.json").exists())
    rows, inputs = [], []
    for s in seeds:
        r, ins = check_seed(s)
        rows.append(r)
        inputs.extend(ins)
        print(f"{r['status']:4} {r['arm']} {r['class']:8} {r['id']:30} guards={r.get('guard_ids_ir', '?'):6} "
              f"optnone={r.get('optnone_functions') or '-':4} inputs {r['inputs_ok']}/{r['inputs']}"
              + (f"  !! {r['problems']}" if r["problems"] else ""))
    res = ROOT / "results"
    for name, data in (("m2_seeds.csv", rows), ("m2_inputs.csv", inputs)):
        keys = list(dict.fromkeys(k for d in data for k in d))
        with open(res / name, "w", newline="") as f:
            wr = csv.DictWriter(f, fieldnames=keys)
            wr.writeheader()
            wr.writerows(data)
    (res / "m2_commands.txt").write_text("\n".join(COMMANDS) + "\n")
    for arm in "AB":
        a = [r for r in rows if r["arm"] == arm]
        by = {c: sum(1 for r in a if r["class"] == c) for c in ("bounds", "overflow", "null")}
        print(f"Arm {arm}: {sum(r['status'] == 'OK' for r in a)}/{len(a)} seeds OK, per class {by}, "
              f"inputs ok {sum(r['inputs_ok'] for r in a)}/{sum(r['inputs'] for r in a)}")
    return 0 if all(r["status"] == "OK" for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
