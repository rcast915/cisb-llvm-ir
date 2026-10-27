"""Count security guards in textual LLVM IR.

A guard (scope doc section 4) is a conditional branch whose failing side leads
to an error path. Seeds mark every error path with a call to
@cisb_guard_fail(i32 <id>), so here a guard is:

  a block that calls @cisb_guard_fail, is reachable from the entry block, and
  is entered through a conditional `br i1 %c` / `switch` whose condition is
  not a constant (directly, or through a chain of unconditional branches).

If an optimizer merges several marker calls into one (call with a phi
operand), the ids are recovered from the phi's constant incoming values.
"""
import re
import sys
from dataclasses import dataclass, field

MARKER = "@cisb_guard_fail"
LABEL_RE = re.compile(r'^([A-Za-z$._0-9-]+|"[^"]+"):')
DEFINE_RE = re.compile(r'^define\b[^@]*@([A-Za-z$._0-9-]+|"[^"]+")\((.*)\)')
LABEL_REF_RE = re.compile(r'label %([A-Za-z$._0-9-]+|"[^"]+")')
CALL_RE = re.compile(re.escape(MARKER) + r'\(i32(?: noundef)? (%?[-\w.]+)\)')
TERMINATORS = {"br", "switch", "ret", "unreachable", "indirectbr", "resume", "invoke", "callbr"}
PHI_RE = re.compile(r'^\s*(%[-\w.]+) = phi i32 (.*)$')


@dataclass
class Block:
    name: str
    lines: list = field(default_factory=list)

    @property
    def term(self):
        """Terminator text (multi-line switch joined into one string)."""
        for i in range(len(self.lines) - 1, -1, -1):
            s = self.lines[i].strip()
            if s.split(" ", 1)[0] in TERMINATORS:
                return " ".join(l.strip() for l in self.lines[i:])
        return ""


@dataclass
class Function:
    name: str
    blocks: list
    attrs_line: str

    def block(self, name):
        return next(b for b in self.blocks if b.name == name)


def parse_functions(text):
    funcs, cur, blk = [], None, None
    for raw in text.splitlines():
        line = raw.split(" ;", 1)[0].rstrip()   # drop trailing comments
        if cur is None:
            m = DEFINE_RE.match(raw)
            if m:
                # An unnamed entry block takes the next number after unnamed args.
                nums = [int(x) for x in re.findall(r'%(\d+)\b', m.group(2))]
                blk = Block(str(max(nums) + 1 if nums else 0))
                cur = Function(m.group(1), [blk], raw)
            continue
        if raw.startswith("}"):
            funcs.append(cur)
            cur = blk = None
            continue
        m = LABEL_RE.match(raw)
        if m:
            if len(cur.blocks) == 1 and not blk.lines:   # explicitly labelled entry
                blk.name = m.group(1)
            else:
                blk = Block(m.group(1))
                cur.blocks.append(blk)
            continue
        if line.strip():
            blk.lines.append(line)
    return funcs


def successors(block):
    t = block.term
    if t.split(" ", 1)[0] in ("br", "switch", "indirectbr", "invoke", "callbr"):
        return LABEL_REF_RE.findall(t)
    return []


def is_conditional(block):
    t = block.term
    if t.startswith("br i1 "):
        cond = t[len("br i1 "):].split(",", 1)[0].strip()
        return cond not in ("true", "false")
    if t.startswith("switch "):
        val = t.split()[2].rstrip(",")
        return val.startswith("%")
    return False


def guard_report(func):
    """Return dict: guards (list of {block, ids, conditional}), ids (set of conditional guard ids)."""
    names = [b.name for b in func.blocks]
    succ = {b.name: successors(b) for b in func.blocks}
    preds = {n: [] for n in names}
    for n, ss in succ.items():
        for s in ss:
            if s in preds:
                preds[s].append(n)
    # reachability from entry
    seen, stack = set(), [names[0]]
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        stack.extend(succ.get(n, []))
    phis = {}
    for b in func.blocks:
        for ln in b.lines:
            m = PHI_RE.match(ln)
            if m:
                phis[m.group(1)] = [int(v) for v in re.findall(r'\[\s*(-?\d+)\s*,', m.group(2))]

    def control_dependent(n, depth=0):
        for p in preds[n]:
            pb = func.block(p)
            if p in seen and is_conditional(pb):
                return True
            if depth < 16 and len(succ[p]) == 1 and control_dependent(p, depth + 1):
                return True
        return False

    guards = []
    for b in func.blocks:
        for ln in b.lines:
            m = CALL_RE.search(ln)
            if not m:
                continue
            op = m.group(1)
            ids = [int(op)] if not op.startswith("%") else phis.get(op, [])
            guards.append({"block": b.name, "ids": ids, "reachable": b.name in seen,
                           "conditional": b.name in seen and control_dependent(b.name)})
    ids = sorted({i for g in guards if g["conditional"] for i in g["ids"]})
    return {"function": func.name, "guards": guards, "ids": ids}


def module_guards(text):
    """Per-function guard reports for every defined function that has marker calls."""
    out = {}
    for f in parse_functions(text):
        r = guard_report(f)
        out[f.name] = r
    return out


def count_ids(text):
    return sorted({i for r in module_guards(text).values() for i in r["ids"]})


if __name__ == "__main__":
    import json
    print(json.dumps(module_guards(open(sys.argv[1]).read()), indent=2))
