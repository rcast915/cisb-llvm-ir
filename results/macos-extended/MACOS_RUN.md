# macOS run of the extended corpus (FINDINGS.md Task 5)

Run on 2026-11-24 from `main` at `6156f6f` (38 seeds, 170 inputs) with `scripts/setup.sh`,
`scripts/check_seeds.sh`, `scripts/run_baseline.sh`, `scripts/run_mutants.sh`, then
`tools/recheck_stripped.py` (with `ROOT` set to the repo instead of `/workspace`) and
`tools/compare_runs.py` against `results/linux-extended/`. Total wall time 654 s.

## Toolchain (`versions.txt`)

| | macOS (this run) | Linux Docker (`linux-extended`) |
|---|---|---|
| Host | macOS 26.6.2, Apple M5 Pro (15 cores, 24 GB) | Ubuntu 24.04.5 in Docker on Windows 11, x86-64 |
| SDK | Xcode 27.0 (27A266a), MacOSX.sdk 27.0 | — |
| clang/opt | Homebrew LLVM 23.1.4 (pinned) | apt.llvm.org LLVM 23.1.6 |
| Alive2 | Homebrew 21.0_9 | v21.0 + same two backports |
| Z3 | 5.3.2 | 5.3.2 |
| Target | arm64-apple-macosx26.0.0 | x86_64-pc-linux-gnu |

## Stage results

| Stage | Result |
|---|---|
| M1 self-tests, sanitizer smoke test, unit tests | PASS, PASS, 8/8 |
| M2 seed check | Arm A 25/25 seeds, 130/130 inputs; Arm B 12/13 seeds, 39/40 inputs (see b_ptr04 below) |
| M3 baseline | 228 rows. Arm A 150 rows, **0 candidates**. Arm B 78 rows, 36 candidates (20 LEGAL_UB, 16 UNKNOWN:nofree) |
| M4 mutants | Arm A 32 generated / 23 accepted (9 rejected for UB), 138 rows, **0 candidates**. Arm B 18/18, 108 rows, 46 candidate rows from 14 mutants (32 LEGAL_UB, 14 UNKNOWN:nofree); 15 unattributed divergences, all explained by the UB monitor's pointer-overflow gap |
| Alive2 MISCOMPILE | 0 |
| Attribute-stripped re-check | baseline 64 rows: 48 CORRECT, 6 approximated, 6 timeout, 2 ptrtoaddr, 2 INCORRECT (`a_nul03` O2/O3, the known inlining artefact); mutants 58 rows: 34 CORRECT, 16 approximated, 8 timeout |

Positive-control gate: same as Linux. b_bnd03/04, b_nul01/02, b_ovf01/02, b_ptr01/02/03 PASS;
b_bnd01/02 negative controls unchanged; b_ptr04 and b_ptr05 show no guard removal (b_ptr04 is
detected through divergence instead, below).

## macOS vs Linux (`compare_*_vs_linux-extended.txt`)

* Baseline: **219/228 rows identical** on guard ids, removed/weakened, divergence, candidate, Alive2
  verdict and classification. Mutants: **232/246 identical**.
* 5 baseline + 10 mutant differences are Alive2 only: CORRECT on macOS, `UNKNOWN:smt-timeout` on Linux.
  This settles FINDINGS Task 3's open question for the 5 baseline rows: they verify on macOS in
  0.1-15 s, so the Linux timeouts are an environment effect, not a property of the transformations.
* The other 4 + 4 differences are all `b_ptr04`: `linux-extended` was run before its INT64_MIN input
  was added. With that input, both platforms flag the same rows (InstCombine, O2, O3; see
  `results/investigations/`), but the **-O0 behaviour differs by architecture**:
  * Linux x86-64: the wrapped pointer `p + INT64_MIN` faults (exit -11).
  * macOS arm64: no fault, `ret 113` (the buffer's own byte). Apple Silicon ignores the top byte of
    user-space addresses (Top Byte Ignore), so flipping bit 63 lands back on the original buffer.
    Confirmed with a standalone test (`*(buf + 2^63)` reads `buf[0]`).
  This is why the M2 check fails that one input: its recorded expectation (`asan:SEGV`) is the
  x86-64 outcome. The UB is the same; its visible effect is a crash on one CPU and a silent read on
  the other.
* Attribute-stripped re-check: Arm B candidates resolve to CORRECT on both platforms except
  b_ptr02 O2/O3 (macOS: "approximated", Linux: CORRECT). Several rows are "approximated" on macOS
  where Linux times out; both are UNKNOWN. `a_bnd09` O2/O3 are only re-checked on Linux because on
  macOS Alive2 did not stop at an unsupported attribute for them (it reported "approximated"),
  suggesting the arm64 and x86-64 O2 pipelines infer different attributes there.
