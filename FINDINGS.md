# cisb-llvm-ir: remaining-work results (2026-11-24)

Everything here was produced from a read-only clone of `rcast915/cisb-llvm-ir` at commit `6fca16b`
(public `main`). Nothing was pushed to GitHub; all files in this folder are for the team to review
and commit themselves.

## Folder contents

| Path | What it is |
|---|---|
| `docker/` | Linux Docker toolchain: `Dockerfile` (LLVM 23 + Alive2 v21.0 with the same two backports Homebrew uses), `Dockerfile.z3` (same, linked to Z3 5.3.2 = the macOS solver version), `env.linux.sh` (drop-in replacement for `scripts/env.sh`), `setup_linux.sh` (M1 self-tests), `run_docker.sh` (runs all stages) |
| `new-seeds/` | 5 new pointer-wrap seeds (2 Arm A UB-free rewrites, 3 Arm B controls) |
| `tools/add_boundary_inputs.py` | Appends 32 boundary inputs to 14 existing seeds (tagged `"boundary": true`) |
| `tools/recheck_stripped.py` | Re-runs Alive2 on `UNKNOWN:unsupported-attribute` rows after stripping `nofree`/`nosync`/`captures(...)` |
| `tools/compare_runs.py` | Row-by-row diff of two result CSVs (used for macOS vs Linux) |
| `results/macos-original/` | The committed macOS results (unchanged copy, for reference) |
| `results/linux-docker/` | Original 33-seed corpus re-run in Docker (Z3 5.3.2) + attribute-stripped re-checks |
| `results/linux-extended/` | 38-seed corpus + boundary inputs, full M1–M4 run + re-checks |
| `results/investigations/` | `b_ptr04` re-run with the INT64_MIN wrap input |

### How to run

From Git Bash (Windows) or any bash with Docker running; the checkout must have LF line endings
(`git clone -c core.autocrlf=false ...`):

```sh
bash docker/run_docker.sh /path/to/cisb-llvm-ir            # setup + seeds + baseline + mutants (+ 'shell' for an interactive container)
bash docker/run_docker.sh /path/to/cisb-llvm-ir baseline   # a single stage
```

First build ~5 min (LLVM from apt.llvm.org, Alive2 compile ~2 min on 12 cores); full run ~14 min.
To use the extended corpus: copy `new-seeds/*` into `seeds/` and run `python3 tools/add_boundary_inputs.py seeds`.

## Toolchain recorded for the Linux run

| | macOS (original) | Linux Docker (this run) |
|---|---|---|
| Host | Darwin arm64 26.6.2 | Ubuntu 24.04.5 in Docker 27.5.1 on Windows 11, x86-64 |
| clang/opt | Homebrew LLVM 23.1.4 | apt.llvm.org LLVM 23.1.6 |
| Alive2 | Homebrew 21.0_9 (v21.0 + a86aaa0 + 155386f) | built from v21.0 + same two commits |
| Z3 | 5.3.2 | 5.3.2 (pip `z3-solver`), also tested Ubuntu 4.8.12 |
| Target | arm64-apple-macosx26.0.0 | x86_64-pc-linux-gnu |

Build note: LLVM 23.1.6 deprecates `BranchInst`, and Alive2 builds with `-Werror`; the Dockerfile adds
`-Wno-error=deprecated-declarations` (warnings only, no code change).

---

## Task 1 — Reproduce the run and tests

* Unit tests: 8/8 pass (Python 3.12 in Docker, 3.13 on Windows).
* M1 self-tests: PASS (good/bad/ub_legal/roundtrip + ASan/UBSan smoke). `otool` message is cosmetic (macOS-only diagnostic).
* M2: 33/33 seeds OK, 116/116 inputs, identical to macOS.
* **M3 baseline: 193 of 198 rows identical to macOS** on guard ids, removed/weakened guards, divergences,
  candidate flag, Alive2 verdict and classification. The 5 differing rows differ **only** in Alive2
  (`CORRECT` on macOS → `UNKNOWN:smt-timeout` on Linux). Arm A: 0 candidates. Arm B: same 30 candidates,
  all 8 positive controls PASS, both negative controls unchanged.
* **M4 mutants: 43 generated / 35 accepted (same as macOS); 201 of 210 rows identical**, again the 9
  differences are only SMT timeouts. Arm A mutants: 0 candidates. Arm B: 40 candidate rows from 12 mutants.
* Conclusion: the headline result (no Arm A miscompile; all positive controls detected) reproduces on a
  second OS, CPU architecture and LLVM patch release.

## Task 2 — The two unresolved Alive2 loop-copy diagnostics (`a_bnd05_loop_copy`, O2 and O3)

1. Original label `UNKNOWN:unsupported-attribute:nofree` — Alive2 v21 cannot parse the `nofree`
   attribute that `default<O2|O3>` infers.
2. After stripping caller-facing attributes (`nofree`, `nosync`, `captures(...)`) the rows hit a **second**
   blocker: `Unsupported instruction: ptrtoaddr`. At O2/O3 the loop vectorizer turns `copy_words` into a
   4-wide vector loop guarded by a runtime overlap check (`vector.memcheck`), and LLVM 23 emits that check
   with the new `ptrtoaddr` instruction, which Alive2 v21 predates.
3. Workarounds tried:
   * O2 with vectorization forced off (`-force-vector-width=1 -force-vector-interleave=1`): **Alive2 CORRECT**
     (bounded to the seed's unroll of 8).
   * Real O2/O3 output with `ptrtoaddr` replaced by `ptrtoint`: Alive2 **times out** (20 s) on the vector body.
4. Runtime: no divergence on any input, including new boundary inputs `8 8`, `8 9`, `12 12`, `0 0`.

**Status for the report:** the non-vectorized O2 pipeline is verified; the vectorized loop remains
`UNKNOWN` because Alive2 v21 cannot model `ptrtoaddr` and the vector body exceeds the SMT budget.
Also note the unroll bound is in *iterations of each function's loop*: after 4-wide vectorization, 8
target iterations cover more scalar work than 8 source iterations, so even a CORRECT here would be bounded.

## Task 3 — SMT timeouts, validator assumptions, UB attribution

### SMT timeouts are environment-dependent
* With Ubuntu's Z3 4.8.12: 7 baseline rows flip CORRECT → timeout vs macOS; rows that took 0.08–0.65 s on
  macOS did not finish even with a 120 s limit.
* Linking Alive2 to Z3 5.3.2 (the macOS version) fixed 2 of the 7 (`a_bnd02`, `a_bnd04`).
* Re-targeting the IR to `arm64-apple-macosx` gave **identical** timing → the CPU target is not the cause.
* The remaining 5 (`a_bnd08`/instcombine, `a_nul04`/simplifycfg, `a_ovf07`/simplifycfg,
  `b_ptr02`/instcombine+simplifycfg) still time out. Most involve `memcpy` with a symbolic length or
  pointer comparisons (expensive in Alive2's memory model). Remaining suspects: LLVM 23.1.4 vs 23.1.6 pass
  output, or Homebrew's Z3/Alive2 build. Could be settled by Ray running `alive-tv` on our `.ll` files.
* **For the report:** UNKNOWN:smt-timeout counts are not portable; they vary with solver version and build.
  The pipeline handles this correctly (timeouts are never counted as CORRECT), and no guard/divergence/
  candidate decision depended on them. The interim report's "SIZE_MAX / sz ... (7 UNKNOWN rows)" is slightly
  off: 6 of the 7 are `a_ovf03_mul_alloc`; the 7th is `a_ovf06_usub_underflow` under InstCombine.

### Validator assumptions
* **Unsupported attributes (`nofree`, `captures`)** hide most O2/O3 rows. Re-checking with the attributes
  stripped from both sides (`tools/recheck_stripped.py`):
  * baseline: 58 rows → 44 CORRECT, 10 smt-timeout, 2 `ptrtoaddr` (loop-copy), **2 INCORRECT** (below);
  * **all 12 Arm B baseline candidates and all 10 Arm B mutant candidates that were UNKNOWN become CORRECT**,
    i.e. they are UB-licensed (LEGAL_UB) removals, not miscompiles;
  * mutants: 52 rows → 34 CORRECT, 18 smt-timeout, 0 INCORRECT.
  Caveat to state: this validates the optimized function *body*; it does not validate the inferred
  attributes themselves. Report these as "CORRECT (attributes stripped)".
* **False alarm from inlining — `a_nul03_lookup` O2/O3 `INCORRECT`.** Once the attribute error is removed,
  Alive2 reports "Source is more defined than target" (counterexample `t = null, n = 0`). The seed's
  `lookup` calls a separate static `find`; Alive2 treats that call as opaque, while O2 inlines `find`.
  Proof that this is Alive2's documented interprocedural limitation and not an LLVM bug: Alive2 also rejects
  the **inlining step alone** (seed → seed with `find` inlined, no other optimization), which is
  semantics-preserving. Against the inlined source the O2 output gives no counterexample (timeout), guards
  are unchanged and there is no runtime divergence. Recommendation: either inline helpers in the seed IR
  before validation, or label rows where a defined callee disappears as `UNKNOWN:interprocedural`.
* `classify()` maps `NO_TRANSFORM` on a candidate row to LEGAL_UB/BENIGN; a candidate with no transform is
  contradictory and would be safer as UNKNOWN (did not occur in any run).

### UB attribution / differential oracle
* `classify()` labels a candidate LEGAL_UB if the seed is UB-by-construction **or any** input produced a
  sanitizer report — not specifically the divergent input. Harmless for current results (Arm A is
  sanitizer-clean), but per-input attribution would be stricter.
* The divergence oracle compares exit code + `GUARD` lines only; other stdout (`ret ...`) is recorded in
  `stdout_diff_inputs` but does not make a row a candidate. On macOS 10 Arm B mutant rows had stdout-only
  differences (even under the `sroa` control). Explained: those `pred_flip` mutants let `i == n` through,
  so the program prints an **out-of-bounds heap value**; on Linux that slot reads 0 in every build, so the
  same rows show no difference. Not a missed miscompile (Arm B is UB by design), but it means a
  value-changing miscompile with an unchanged guard would not be flagged. Arm A has 0 such rows on both
  platforms. Suggest counting `stdout_diff` as a candidate signal for Arm A.

## Task 4 — Coverage: pointer-wrap seeds and boundary inputs

Extended corpus: **38 seeds** (Arm A 25, Arm B 13), **170 inputs** (116 original + 32 boundary inputs on 14
existing seeds + 22 inputs on the new seeds), all passing the seed checker on the first run.

New seeds:

| Seed | Arm | Pattern | Result |
|---|---|---|---|
| `a_bnd09_ptr_range_safe` | A | UB-free rewrite of b_ptr02: `len > end - p` | guards 42, 43 kept under every pipeline, Alive2 CORRECT |
| `a_bnd10_uintptr_wrap` | A | UB-free rewrite of b_ptr01: wrap test on `uintptr_t` | guard 44 kept under every pipeline |
| `b_ptr03_wrap_ge` | B | inverted polarity `!(p + len >= p)` | **detected**: InstCombine/O2/O3 delete the guard (function becomes `ret 0`) |
| `b_ptr04_wrap_signed_off` | B | `p + off < p`, signed `off` | LLVM rewrites the pointer test to `off < 0`. Invisible on ordinary inputs; with the added INT64_MIN input the **-O0 build bypasses its own check and segfaults, while InstCombine/O2/O3 reject it** (divergence, Alive2 CORRECT → LEGAL_UB). Optimized build is *safer*, like b_nul01 |
| `b_ptr05_wrap_int_len` | B | 32-bit signed `len` | LLVM rewrites to `len < 0`, but a 32-bit length cannot wrap a 64-bit pointer, so behaviour never changes → acts as a negative control |

Extended-run headline numbers (Linux, Z3 5.3.2):

| Measure | Arm A | Arm B |
|---|---|---|
| Seeds / inputs | 25 / 130 | 13 / 40 |
| Baseline rows / candidates | 150 / 0 | 78 / 33 (+3 for b_ptr04 with the wrap input) |
| Mutants generated / accepted | 32 / 23 | 18 / 18 |
| Mutant candidates | 0 | 43 rows from 13 mutants |
| Alive2 MISCOMPILE | 0 | 0 |
| Unexplained divergences | 0 | 0 |

The two UB-free pointer-range rewrites are a useful contrast for the report: the UB-dependent forms
(b_ptr01/02/03) lose their guards, the defined forms (a_bnd09/10) never do.

## Task 5 — macOS run

Not done here (Windows machine). Whoever has the Mac should re-run `scripts/setup.sh`,
`scripts/check_seeds.sh`, `scripts/run_baseline.sh`, `scripts/run_mutants.sh` and record
`results/versions.txt` (macOS version, chip, Xcode SDK, LLVM/Alive2/Z3). The Linux column of the toolchain
table above is the second platform for comparison.

## Task 6 — Tests vs generated artifacts

* Committed results match the interim report's Table 1 exactly (138/0, 60/30 with 18 LEGAL_UB + 12 UNKNOWN,
  29/21 and 14/14 mutants, 126/0, 84/40 with 30 LEGAL_UB + 10 UNKNOWN; UB monitor 114/116, misses are the
  two pointer-overflow inputs of b_ptr01/b_ptr02).
* Inconsistencies found:
  1. README milestone table says "31 seeds"; the corpus and the rest of the README have **33**.
  2. The report cites commit `553fede`; that commit is **not** in the public repo (HEAD is `6fca16b`).
     Push it or cite `6fca16b`.
  3. "SIZE_MAX / sz ... (7 UNKNOWN rows)": 6 are `a_ovf03`, 1 is `a_ovf06` (see Task 3).
  4. Report timeline dates (Nov 8–20) have passed.

## Suggested lines for the final report

* *Reproducibility.* "We reproduced the full pipeline in a Linux Docker container (Ubuntu 24.04, LLVM
  23.1.6, Alive2 v21.0 with the same backports, Z3 5.3.2, x86-64). 193/198 baseline rows and 201/210 mutant
  rows matched the macOS run exactly; every difference was an SMT timeout, and no guard, divergence or
  candidate decision changed."
* *Validator limits.* "Alive2 v21 cannot parse attributes inferred at -O2/-O3 and LLVM 23's `ptrtoaddr`.
  Stripping caller-facing attributes resolved all 22 Arm B UNKNOWN candidates to valid refinements. One
  apparent counterexample (a_nul03 at -O2/-O3) is an artefact of inlining, since Alive2 rejects the
  inlining step alone."
* *Coverage.* "Five pointer-wrap seeds and 54 new inputs (32 boundary values on existing seeds) were added. UB-free rewrites of the wrap
  checks keep their guards under every pipeline, while the UB-dependent forms are removed or rewritten; for
  the signed-offset form the rewrite makes the optimized build safer than -O0."
