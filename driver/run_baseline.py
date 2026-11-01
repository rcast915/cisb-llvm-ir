#!/usr/bin/env python3
"""M3 baseline driver. Run via scripts/run_baseline.sh (needs scripts/env.sh).

For every seed and pipeline:
  * opt the seed IR (results row: guard ids before/after, removed/weakened ids, time)
  * behavioural differential with PLAIN builds (no sanitizers): the unoptimized
    seed IR and the optimized IR are each code-generated with `clang -O0` and
    linked with the same main/harness; every input is run on both, comparing
    exit code and GUARD lines.
  * UB attribution from a SEPARATE -O0 ASan+UBSan build of the source (never
    used as the divergence oracle).
  * alive-tv seed.ll after.ll (translation validation of the whole pipeline).

Pipelines: isolated passes run after the fixed prelude `sroa` (nothing else).
"""
import csv
import json
import os
import re
import shlex
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import irguards  # noqa: E402
from check_seeds import ROOT, SYS, IRFLAGS, SANFLAGS, RUN_ENV, CLANG, OPT, run, report_kinds, COMMANDS  # noqa: E402

ALIVE_TV = os.environ["ALIVE_TV"]
LLVM_EXTRACT = str(Path(OPT).parent / "llvm-extract")
PRELUDE = "sroa"
PIPELINES = [  # (name, -passes string)
    ("sroa", "sroa"),
    ("sroa+instcombine", "sroa,instcombine"),
    ("sroa+simplifycfg", "sroa,simplifycfg"),
    ("sroa+gvn", "sroa,gvn"),
    ("O2", "default<O2>"),
    ("O3", "default<O3>"),
]
WORK = ROOT / "work" / "m3"
ALIVE_SMT_MS = 10000
ALIVE_PROC_S = 300
RUN_S = 10


def defined_external_symbols(ll_text):
    """Externally visible functions/globals defined in a module (to drop from main's module)."""
    funcs, globs = [], []
    for ln in ll_text.splitlines():
        if ln.startswith("define "):
            head = ln.split("@", 1)[0]
            if not re.search(r"\b(internal|private)\b", head):
                funcs.append(re.match(r"[^@]*@([\w.$]+)\(", ln).group(1))
        elif ln.startswith("@") and re.search(r"\bglobal\b", ln):
            name, rhs = ln[1:].split(" = ", 1)
            if not re.match(r"(internal|private|external|extern_weak)\b", rhs):
                globs.append(name)
    return funcs, globs


def build_plain(meta, w):
    """Return (main_obj, harness_obj); compile seed.ll; everything codegen'd at -O0, no sanitizers."""
    seed_c = ROOT / "seeds" / meta["id"] / "seed.c"
    seed_ll, full_ll, rest_ll = w / "seed.ll", w / "full.ll", w / "main_rest.ll"
    for cmd in ([CLANG, *SYS, *IRFLAGS, seed_c, "-o", seed_ll],
                [CLANG, *SYS, *IRFLAGS, "-DSEED_MAIN", seed_c, "-o", full_ll]):
        rc, _, err, _ = run(cmd, 60)
        if rc != 0:
            raise RuntimeError(err)
    funcs, globs = defined_external_symbols(seed_ll.read_text())
    cmd = [LLVM_EXTRACT, "--delete", "-S", *[f"--func={f}" for f in funcs], *[f"--glob={g}" for g in globs], full_ll, "-o", rest_ll]
    for c in ([*cmd],
              [CLANG, *SYS, "-O0", "-c", rest_ll, "-o", w / "main_rest.o"],
              [CLANG, *SYS, "-O0", "-c", ROOT / "seeds/common/harness.c", "-o", w / "harness.o"]):
        rc, _, err, _ = run(c, 60)
        if rc != 0:
            raise RuntimeError(f"{c[0]}: {err}")
    return w / "main_rest.o", w / "harness.o"


def link_variant(ll, w, tag, main_o, harness_o):
    obj, exe = w / f"{tag}.o", w / f"{tag}.plain"
    for c in ([CLANG, *SYS, "-O0", "-c", ll, "-o", obj], [CLANG, *SYS, main_o, harness_o, obj, "-o", exe]):
        rc, _, err, _ = run(c, 60)
        if rc != 0:
            raise RuntimeError(f"link {tag}: {err}")
    return exe


def run_inputs(exe, meta):
    res = []
    for inp in meta["inputs"]:
        rc, out, err, dt = run([exe, *inp["args"]], RUN_S)
        res.append({"exit": rc, "guards": tuple(re.findall(r"^GUARD (\d+)$", out, re.M)), "stdout": out.strip()})
    return res


def sanitizer_attribution(meta, w):
    exe = w / "seed_san"
    rc, _, err, _ = run([CLANG, *SYS, *SANFLAGS, "-DSEED_MAIN", ROOT / "seeds" / meta["id"] / "seed.c",
                         ROOT / "seeds/common/harness.c", "-o", exe], 120)
    if rc != 0:
        raise RuntimeError(err)
    return [report_kinds(run([exe, *i["args"]], RUN_S, env=RUN_ENV)[2]) for i in meta["inputs"]]


def alive2(before, after, meta):
    cmd = [ALIVE_TV, f"--smt-to={ALIVE_SMT_MS}"]
    if meta["loops"]:
        cmd += [f"--src-unroll={meta['alive2_unroll']}", f"--tgt-unroll={meta['alive2_unroll']}"]
    rc, out, err, dt = run([*cmd, before, after], ALIVE_PROC_S)
    text = out + err
    if rc == "TIMEOUT":
        return "UNKNOWN", "process-timeout", dt, text
    n = {k: int(m.group(1)) if (m := re.search(rf"(\d+) {k}", text)) else 0
         for k in ("correct transformations", "incorrect transformations", "failed-to-prove transformations", "Alive2 errors")}
    errors = list(dict.fromkeys(re.findall(r"ERROR: (.*)", text)))
    detail = (f"correct={n['correct transformations']} incorrect={n['incorrect transformations']} "
              f"ftp={n['failed-to-prove transformations']} err={n['Alive2 errors']}"
              + (" | " + " ; ".join(errors[:3]) if errors else ""))
    if n["incorrect transformations"]:
        return "INCORRECT", detail, dt, text
    if n["Alive2 errors"] or n["failed-to-prove transformations"]:
        joined = " ".join(errors)
        m = next((mm for e in errors if (mm := re.match(r"Unsupported (attribute|instruction|metadata|type): *(.*)$", e))), None)
        if m:
            what = m.group(2).strip()
            if m.group(1) == "instruction":
                im = re.search(r"@(llvm\.[a-z_]+(?:\.[a-z_]+)?)", what)
                what = im.group(1) if im else what.split()[0]
            elif m.group(1) == "metadata":
                what = {"1": "tbaa"}.get(what, what)
            sub = f"unsupported-{m.group(1)}:{what}"
        else:
            sub = ("smt-timeout" if re.search(r"[Tt]imeout", joined) else
                   "approximated" if "approximat" in text else
                   "translate-error" if "Could not translate" in joined else "alive2-error")
        return "UNKNOWN", f"{sub} | {detail}", dt, text
    if n["correct transformations"]:
        return "CORRECT", detail, dt, text
    return "NO_TRANSFORM", detail, dt, text


def classify(candidate, verdict, alive_detail, ub_on_inputs, ub_by_construction):
    if not candidate:
        return "-"
    if verdict == "INCORRECT":
        return "MISCOMPILE"
    if verdict == "UNKNOWN":
        return "UNKNOWN:" + alive_detail.split(" |", 1)[0]
    if verdict in ("CORRECT", "NO_TRANSFORM"):
        return "LEGAL_UB" if (ub_by_construction or ub_on_inputs) else "BENIGN"
    return "UNKNOWN:alive2-error"


def evaluate_pipelines(meta, src_ll, w, ref, san, main_o, harness_o, base_row, pipelines=None):
    """Run every pipeline on src_ll; compare against `ref` (plain -O0 runs of src_ll).
    `san` = per-input UB reports used only for attribution. Returns one row per pipeline."""
    before_ids = irguards.count_ids(Path(src_ll).read_text())

    def one(pl):
        name, passes = pl
        after = w / f"{name}.ll"
        rc, _, err, dt = run([OPT, "-S", f"-passes={passes}", src_ll, "-o", after], 120)
        row = {**base_row, "pipeline": name, "prelude": PRELUDE if name.startswith("sroa") else "none (full pipeline)",
               "opt_passes": passes, "guard_ids_before": " ".join(map(str, before_ids))}
        if rc != 0:
            row.update(status="OPT_FAIL", detail=err.strip().splitlines()[0][:200] if err.strip() else str(rc),
                       opt_secs=f"{dt:.3f}", candidate=False, classification="-")
            return row
        row["opt_secs"] = f"{dt:.3f}"
        after_ids = irguards.count_ids(after.read_text())
        removed = [i for i in before_ids if i not in after_ids]
        var = run_inputs(link_variant(after, w, name, main_o, harness_o), meta)
        div, weakened = [], set()
        for k, (r0, r1) in enumerate(zip(ref, var)):
            for g in r0["guards"]:
                if int(g) in after_ids and g not in r1["guards"]:
                    weakened.add(int(g))
            if (r0["exit"], r0["guards"]) != (r1["exit"], r1["guards"]):
                div.append((k, r0, r1, san[k]))
        row.update({
            "guard_ids_after": " ".join(map(str, after_ids)),
            "removed_ids": " ".join(map(str, removed)),
            "weakened_ids": " ".join(map(str, sorted(weakened))),
            "n_inputs": len(ref),
            "divergent_inputs": len(div),
            "divergent_ub_attributed": sum(1 for d in div if d[3]),
            "divergent_unattributed": sum(1 for d in div if not d[3]),
            "divergence_detail": " ; ".join(
                f"in{k} {meta['inputs'][k]['args']}: O0(exit={a['exit']},G={list(a['guards'])}) "
                f"opt(exit={b['exit']},G={list(b['guards'])}) san0={'+'.join(s) or 'clean'}" for k, a, b, s in div),
            "stdout_diff_inputs": sum(1 for r0, r1 in zip(ref, var) if r0["stdout"] != r1["stdout"]),
        })
        verdict, detail, adt, text = alive2(src_ll, after, meta)
        (w / f"{name}.alive.txt").write_text(text)
        candidate = bool(removed or weakened or div)
        row.update({"candidate": candidate, "alive2_verdict": verdict, "alive2_detail": detail,
                    "alive2_secs": f"{adt:.2f}", "alive2_unroll": meta["alive2_unroll"] if meta["loops"] else 0,
                    "classification": classify(candidate, verdict, detail, any(san), meta["ub_by_construction"]),
                    "status": "OK"})
        return row

    with ThreadPoolExecutor(max_workers=6) as ex:
        return list(ex.map(one, pipelines or PIPELINES))


def process_seed(sdir):
    meta = json.loads((sdir / "inputs.json").read_text())
    w = WORK / meta["id"]
    w.mkdir(parents=True, exist_ok=True)
    main_o, harness_o = build_plain(meta, w)
    seed_ll = w / "seed.ll"
    ref = run_inputs(link_variant(seed_ll, w, "O0ref", main_o, harness_o), meta)
    san = sanitizer_attribution(meta, w)
    base = {"arm": meta["arm"], "seed": meta["id"], "class": meta["class"],
            "ub_by_construction": meta["ub_by_construction"], "ub_pattern": meta.get("ub_pattern", ""),
            "control_role": meta.get("control_role", "")}
    return evaluate_pipelines(meta, seed_ll, w, ref, san, main_o, harness_o, base)


COLUMNS = ["arm", "seed", "class", "ub_by_construction", "ub_pattern", "control_role", "pipeline", "prelude", "opt_passes",
           "guard_ids_before", "guard_ids_after", "removed_ids", "weakened_ids", "opt_secs",
           "n_inputs", "divergent_inputs", "divergent_ub_attributed", "divergent_unattributed",
           "stdout_diff_inputs", "candidate", "alive2_verdict", "alive2_unroll", "alive2_secs",
           "classification", "status", "alive2_detail", "divergence_detail", "detail"]
HEADER = ("# M3 baseline. Isolated pipelines = fixed prelude 'sroa' then exactly one pass "
          "(opt -passes=sroa,<pass>); 'sroa' row = prelude alone; O2/O3 = opt -passes=default<O2|O3> on the same seed IR. "
          "Seed IR: clang $CLANG_IRFLAGS. Plain builds: every module codegen'd with clang -O0, no sanitizers. "
          "UB attribution: separate -O0 ASan+UBSan source build. Alive2: alive-tv seed.ll <pipeline>.ll, "
          f"--smt-to={ALIVE_SMT_MS}, unroll=alive2_unroll for loop seeds. weakened = guard id still in IR "
          "but an input that printed GUARD at O0 no longer does.\n")


def main():
    seeds = sorted(p for p in (ROOT / "seeds").iterdir() if (p / "inputs.json").exists())
    only = set(sys.argv[1:])
    if only:
        seeds = [s for s in seeds if s.name in only]
    t0 = time.monotonic()
    all_rows = []
    for s in seeds:
        rows = process_seed(s)
        all_rows += rows
        for r in rows:
            print(f"{r['arm']} {r['seed']:28} {r['pipeline']:17} ids {r['guard_ids_before']:>3} -> {r.get('guard_ids_after', '?'):>3} "
                  f"rm={r.get('removed_ids') or '-':3} wk={r.get('weakened_ids') or '-':3} div={r.get('divergent_inputs', '?')} "
                  f"alive={r.get('alive2_verdict', '?'):12} cls={r.get('classification', '?')}", flush=True)
    out = ROOT / "results" / "baseline.csv"
    with open(out, "w", newline="") as f:
        f.write(HEADER)
        wr = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        wr.writeheader()
        wr.writerows(all_rows)
    (ROOT / "results" / "m3_commands.txt").write_text("\n".join(COMMANDS) + "\n")
    print(f"wrote {out} ({len(all_rows)} rows) in {time.monotonic() - t0:.1f}s")


if __name__ == "__main__":
    main()
