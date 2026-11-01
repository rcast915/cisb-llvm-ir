"""Dynamic UB check of an IR module (seed or mutant) on a seed's inputs.

Builds: <module> instrumented by ubmon + ASan, codegen at -O0, linked with the
seed's main (main_rest.o) and harness. Returns per-input report kinds
("asan:<kind>" / "ubmon:<kind>"). Used to filter Arm A mutants and to
attribute divergences to UB for mutants.
"""
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ubmon  # noqa: E402
from check_seeds import ROOT, SYS, CLANG, RUN_ENV, run  # noqa: E402

RUN_S = 10


def build(ll, w, tag, main_o, harness_o):
    text, kinds = ubmon.instrument(Path(ll).read_text())
    mon_ll, obj, rt_o, exe = w / f"{tag}.ubmon.ll", w / f"{tag}.ubmon.o", w / "ubmon_rt.o", w / f"{tag}.ubmon"
    mon_ll.write_text(text)
    steps = [[CLANG, *SYS, "-O0", "-fsanitize=address", "-c", mon_ll, "-o", obj]]
    if not rt_o.exists():
        steps.append([CLANG, *SYS, "-O0", "-c", ROOT / "seeds/common/ubmon_rt.c", "-o", rt_o])
    steps.append([CLANG, *SYS, "-fsanitize=address", main_o, harness_o, rt_o, obj, "-o", exe])
    for c in steps:
        rc, _, err, _ = run(c, 120)
        if rc != 0:
            raise RuntimeError(f"ubmon build {tag}: {err[-400:]}")
    return exe, kinds


def check(exe, kinds, meta):
    res = []
    for inp in meta["inputs"]:
        rc, out, err, _ = run([exe, *inp["args"]], RUN_S, env=RUN_ENV)
        rep = []
        for ln in err.splitlines():
            m = re.search(r"ERROR: AddressSanitizer: ([\w-]+)", ln)
            k = ("asan:" + m.group(1)) if m else None
            m2 = re.match(r"UBMON: site (\d+)$", ln)
            if m2:
                k = "ubmon:" + kinds.get(int(m2.group(1)), "?")
            if k and (not rep or rep[-1] != k):
                rep.append(k)
        res.append({"exit": rc, "reports": rep, "guards": re.findall(r"^GUARD (\d+)$", out, re.M)})
    return res
