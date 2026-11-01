"""IR-level UB monitor ("UBSan-lite" for textual LLVM IR).

UBSan checks are inserted by clang's C front end, so they cannot be added to a
mutated .ll file. This module rewrites an IR module so that, before each
instruction that would produce poison/UB for the current operands, it calls
@cisb_ub(i1 <is_ub>, i32 <site>) (defined in seeds/common/ubmon_rt.c, which
prints "UBMON: site <n>" to stderr and continues, like UBSan's recover mode;
instrument() returns the site -> kind map). It also adds `sanitize_address` to
every attribute group so ASan instruments the module (clang only adds it for C
input). Combined with ASan, this is the dynamic UB check for mutants.

Monitored:   add/sub/mul with nsw and/or nuw (signed/unsigned wrap),
             shl/lshr/ashr with shift amount >= bit width,
             udiv/sdiv/urem/srem by zero, sdiv/srem INT_MIN / -1.
NOT monitored (documented gap): poison from getelementptr inbounds/nuw
             arithmetic that is never dereferenced, `exact`/`disjoint`/
             `nneg`/`samesign` flags (absent from clang's unoptimized IR),
             uninitialised loads. Dereferences are covered by ASan.
"""
import re

ARITH_RE = re.compile(r"^(\s*)(%[-\w.]+) = (add|sub|mul)((?: (?:nuw|nsw))+) (i\d+) ([^,]+), (.+?)\s*$")
SHIFT_RE = re.compile(r"^(\s*)(%[-\w.]+) = (shl|lshr|ashr)((?: (?:nuw|nsw|exact))*) (i\d+) ([^,]+), (.+?)\s*$")
DIV_RE = re.compile(r"^(\s*)(%[-\w.]+) = (udiv|sdiv|urem|srem)((?: exact)?) (i\d+) ([^,]+), (.+?)\s*$")


def instrument(ll_text):
    """Return (instrumented_text, {site: kind})."""
    out, kinds, need_decl = [], {}, set()
    site = 0

    def check(indent, cond_lines, kind):
        nonlocal site
        site += 1
        kinds[site] = kind
        tag = f"%__ub{site}"
        lines = [l.replace("@T", tag) for l in cond_lines]
        lines.append(f"call void @cisb_ub(i1 {tag}, i32 {site})")
        return [indent + l for l in lines]

    in_func = False
    for line in ll_text.splitlines():
        if line.startswith("define "):
            in_func = True
        elif line.startswith("}"):
            in_func = False
        if in_func:
            m = ARITH_RE.match(line)
            if m:
                ind, _, op, flags, ty, a, b = m.groups()
                for fl, sign in (("nsw", "s"), ("nuw", "u")):
                    if fl in flags.split():
                        intr = f"llvm.{sign}{op}.with.overflow.{ty}"
                        need_decl.add((intr, ty))
                        out += check(ind, [f"@T.p = call {{ {ty}, i1 }} @{intr}({ty} {a}, {ty} {b})",
                                           f"@T = extractvalue {{ {ty}, i1 }} @T.p, 1"],
                                     f"{'signed' if sign == 's' else 'unsigned'}-{op}-overflow")
            m = SHIFT_RE.match(line)
            if m:
                ind, _, op, flags, ty, a, b = m.groups()
                out += check(ind, [f"@T = icmp uge {ty} {b}, {ty[1:]}"], f"{op}-amount-too-large")
            m = DIV_RE.match(line)
            if m:
                ind, _, op, flags, ty, a, b = m.groups()
                out += check(ind, [f"@T = icmp eq {ty} {b}, 0"], f"{op}-by-zero")
                if op in ("sdiv", "srem"):
                    bits = int(ty[1:])
                    out += check(ind, [f"@T.a = icmp eq {ty} {a}, {-(1 << (bits - 1))}",
                                       f"@T.b = icmp eq {ty} {b}, -1",
                                       f"@T = and i1 @T.a, @T.b"], f"{op}-int-min-by-minus-one")
        out.append(line)
    # ASan only instruments functions with `sanitize_address`, which clang adds
    # in its C front end; IR input has none, so add it to every attribute group.
    out = [re.sub(r"^(attributes #\d+ = \{)", r"\1 sanitize_address", l) if l.startswith("attributes #") else l
           for l in out]
    existing = set(re.findall(r"^declare [^@]*@([\w.]+)\(", ll_text, re.M))
    decls = ["declare void @cisb_ub(i1, i32)"] if "cisb_ub" not in existing else []
    decls += [f"declare {{ {ty}, i1 }} @{intr}({ty}, {ty})" for intr, ty in sorted(need_decl) if intr not in existing]
    return "\n".join(out) + "\n\n" + "\n".join(decls) + "\n", kinds


def report_sites(stderr):
    """Ordered, de-duplicated UBMON kinds from a run's stderr."""
    out = []
    for m in re.finditer(r"^UBMON: site (\d+)$", stderr, re.M):
        out.append(int(m.group(1)))
    return out
