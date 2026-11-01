#!/usr/bin/env python3
"""UB-aware IR mutator (text-level, one-line edits on the seed's unoptimized IR).

Mutation points: the `icmp` that defines the condition of a conditional branch
controlling a guard block (a block calling @cisb_guard_fail), found with
driver/irguards.py. Only the comparison that directly feeds the guard branch is
mutated (for `a && b` guards only the inner condition is reachable this way).

Operators
  pred_flip  strict <-> non-strict: ult<->ule, ugt<->uge, slt<->sle, sgt<->sge
  const_pm1  integer constant operand of the icmp +1 and -1 (skipped if it would
             leave the type's range); pointer/null operands are never touched

Static UB filter (applied to every mutant, both arms):
  * exactly one line differs from the seed, and it is the targeted icmp;
  * the multiset of poison/UB/attribute tokens (nsw, nuw, inbounds, nonnull,
    exact, disjoint, nneg, samesign, noundef, align, dereferenceable, range,
    poison, undef, ...) on that line is unchanged, i.e. no flag is added;
  * `opt -passes=verify` accepts the mutant.
The dynamic UB filter (Arm A: mutant must be UB-free on the seed's inputs under
ASan + the IR UB monitor) is applied by driver/run_mutants.py.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "driver"))
import irguards  # noqa: E402

FLIP = {"ult": "ule", "ule": "ult", "ugt": "uge", "uge": "ugt",
        "slt": "sle", "sle": "slt", "sgt": "sge", "sge": "sgt"}
FLAG_TOKENS = {"nsw", "nuw", "inbounds", "nonnull", "exact", "disjoint", "nneg", "samesign", "noundef",
               "poison", "undef", "inrange", "dereferenceable", "dereferenceable_or_null", "align", "range",
               "noalias", "nofree", "captures", "readonly", "writeonly", "freeze"}
ICMP_RE = re.compile(r"^(\s*)(%[-\w.]+) = icmp ((?:samesign )?)(\w+) (i\d+|ptr) (.+?), (.+?)\s*$")
OPERATORS = ("pred_flip", "const_pm1")


def guard_conditions(ll_text):
    """{function name: set of %cond names feeding conditional branches that control a guard}."""
    out = {}
    for f in irguards.parse_functions(ll_text):
        names = [b.name for b in f.blocks]
        succ = {b.name: irguards.successors(b) for b in f.blocks}
        preds = {n: [] for n in names}
        for n, ss in succ.items():
            for s in ss:
                if s in preds:
                    preds[s].append(n)
        guard_blocks = [g["block"] for g in irguards.guard_report(f)["guards"] if g["conditional"]]
        conds, seen = set(), set()
        stack = list(guard_blocks)
        while stack:
            n = stack.pop()
            for p in preds[n]:
                pb = f.block(p)
                if irguards.is_conditional(pb) and pb.term.startswith("br i1 "):
                    conds.add(pb.term[len("br i1 "):].split(",", 1)[0].strip())
                elif len(succ[p]) == 1 and p not in seen:
                    seen.add(p)
                    stack.append(p)
        if conds:
            out[f.name] = conds
    return out


def function_ranges(lines):
    ranges, cur = {}, None
    for i, ln in enumerate(lines):
        if ln.startswith("define "):
            cur = (re.match(r"[^@]*@([\w.$]+)\(", ln).group(1), i)
        elif ln.startswith("}") and cur:
            ranges[cur[0]] = (cur[1], i)
            cur = None
    return ranges


def in_range(v, ty):
    bits = int(ty[1:])
    return -(1 << (bits - 1)) <= v <= (1 << bits) - 1 and (bits > 1)


def mutation_points(ll_text):
    lines = ll_text.splitlines()
    conds = guard_conditions(ll_text)
    pts = []
    for fn, (a, b) in function_ranges(lines).items():
        for i in range(a, b):
            m = ICMP_RE.match(lines[i])
            if m and m.group(2) in conds.get(fn, ()):
                pts.append((fn, i, m))
    return lines, pts


def mutants(ll_text):
    """Yield (op, function, line_no, before, after, mutated_text)."""
    lines, pts = mutation_points(ll_text)
    for fn, i, m in pts:
        ind, res, fl, pred, ty, x, y = m.groups()
        cands = []
        if pred in FLIP:
            cands.append(("pred_flip", f"{ind}{res} = icmp {fl}{FLIP[pred]} {ty} {x}, {y}"))
        if ty != "ptr":
            for pos, opnd in ((1, y), (0, x)):
                if re.fullmatch(r"-?\d+", opnd):
                    for d in (+1, -1):
                        v = int(opnd) + d
                        if in_range(v, ty):
                            nx, ny = (x, str(v)) if pos == 1 else (str(v), y)
                            cands.append(("const_pm1", f"{ind}{res} = icmp {fl}{pred} {ty} {nx}, {ny}"))
        for op, new in cands:
            out = list(lines)
            out[i] = new
            yield op, fn, i + 1, lines[i].strip(), new.strip(), "\n".join(out) + "\n"


def static_ub_filter(seed_text, mutant_text):
    """Return None if the mutant passes, else the rejection reason."""
    a, b = seed_text.splitlines(), mutant_text.splitlines()
    if len(a) != len(b):
        return "line-count-changed"
    diff = [(x, y) for x, y in zip(a, b) if x != y]
    if len(diff) != 1:
        return f"{len(diff)}-lines-changed"
    x, y = diff[0]
    if not ICMP_RE.match(y):
        return "changed-line-not-icmp"
    tok = lambda s: sorted(t for t in re.findall(r"[A-Za-z_]+", s) if t in FLAG_TOKENS)
    if tok(x) != tok(y):
        return f"flag-tokens-changed {tok(x)} -> {tok(y)}"
    return None


if __name__ == "__main__":
    text = Path(sys.argv[1]).read_text()
    for op, fn, ln, before, after, mt in mutants(text):
        print(f"{op:10} {fn}:{ln}  {before}  ->  {after}  filter={static_ub_filter(text, mt) or 'ok'}")
