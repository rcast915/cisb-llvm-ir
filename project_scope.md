# Project Scope: Detecting Compiler-Introduced Security Bugs via LLVM IR Mutation and Translation Validation

Course: CS 5352/6362 Computer Security. Interim report due ~Nov 3 (confirm exact date). Final due Nov 20.
Status as of Oct 27: nothing built yet. Original plan had Phase 1-2 done by Oct 25, so the schedule below is compressed.

## 1. Goal (one sentence)

Build a small, automated pipeline that mutates security-check IR, optimizes it with InstCombine / SimplifyCFG / GVN, flags cases where a guard is removed or weakened, and uses Alive2 to classify each case, then report which passes and patterns do this most.

## 2. Research questions (what the final report must answer)

- RQ1: Which of the three passes remove or weaken security checks most often, and for which patterns (bounds, overflow, null)?
- RQ2: Of the flagged cases, how many are legal UB-based eliminations vs. Alive2-confirmed miscompilations vs. unknown (timeout/unsupported)?
- RQ3: What are the detection yield, false-positive rate, and time cost per stage?

## 3. In scope / out of scope

In scope
- Single-function LLVM IR snippets (from small C programs and hand-written IR).
- Three check classes: array bounds, integer wrap/overflow guards, null-pointer checks.
- Passes: InstCombine, SimplifyCFG, GVN, run in isolation and as -O0 vs -O2/-O3.
- Mutation of check predicates and pointer arithmetic, with a UB filter.
- Differential execution with ASan/UBSan, then Alive2 on flagged candidates.

Out of scope (do not do these)
- Coverage-guided fuzzing, backends, LTO, other compilers, whole-program analysis.
- Fixing or upstreaming LLVM bugs (we may *report* a finding in the write-up).
- Attacking or testing any system other than our own locally built LLVM.

## 4. Definitions the pipeline must use consistently

- **Guard**: a conditional branch (or select) whose condition is a security check and whose failing side leads to an error path (return error code, trap, abort, or early return).
- **Guard removed/weakened**: after a pass, the guard's branch is gone, constant-folded, or its predicate is strictly weaker (accepts inputs the original rejected).
- **Candidate**: a (mutant IR, pass) pair where a guard was removed/weakened OR where differential execution diverges.
- **Classification of a candidate (via Alive2)**:
  - `LEGAL_UB`: Alive2 verifies the transformation is a valid refinement. The guard was removable only because the input IR already had UB/poison on the guarded path. Security-relevant but not a compiler bug.
  - `MISCOMPILE`: Alive2 reports the transformation is not a refinement. Potential real LLVM bug. Must be minimized and reproduced.
  - `UNKNOWN`: timeout, unsupported feature, or Alive2 error.
  - `BENIGN`: guard was redundant (e.g., dominated by an identical check); no behavior change.

## 4b. Two experiment arms (important)

A correct compiler should almost never remove a guard in UB-free code, so a UB-free-only study can end with zero candidates. Run two arms and report them separately:

- **Arm A: UB-free hunt.** Seeds and mutants must stay free of UB: strict UB filter (no nsw/nuw/inbounds/nonnull/poison/undef added on guard computations), and each unmutated seed and each mutant is checked sanitizer-clean on its inputs. Any guard removal here is a potential real miscompilation (expected to be rare; a null result is a valid, honestly reported result).
- **Arm B: positive controls (`ub_by_construction`).** 6-8 seeds containing classic CISB patterns that are UB in C: signed overflow check after the add (`a + b < a` with signed ints), pointer-wrap check (`p + len < p`), null check after a dereference, bounds check after the use. These are exempt from the sanitizer-clean rule (UBSan firing at -O0 is expected and is recorded). They validate that the pipeline detects guard removal, and supply the LEGAL_UB cases for the per-pass tables.

Report yield, classification counts, and per-pass rates per arm. Never mix the arms in one headline number.

## 5. Architecture

```
seed C/IR -> clang -S -emit-llvm -O0 (-Xclang -disable-O0-optnone) -> seed.ll
seed.ll -> mutator (+ UB filter) -> mutants/*.ll
mutants -> driver: opt -passes=<pass> (each pass alone) and -O2/-O3
        -> guard-count diff (IR level)  +  build & run with ASan/UBSan on test inputs (behavior level)
flagged candidates -> Alive2 (translation validation on opt's before/after) -> classification
results.csv -> aggregate metrics -> report tables/figures
```

Repo layout:
```
seeds/        C and .ll seed programs + inputs.json (test inputs per seed)
mutator/      mutation operators + UB filter
driver/       run_pipeline.py (opt runs, guard diff, execution harness)
validate/     alive2 wrapper + classifier
results/      results.csv, per-candidate artifacts (kept small)
scripts/      setup/build scripts (LLVM, Alive2)
README.md     setup + status
```

## 6. Environment

- Known facts about this machine (verified by the user): Apple Silicon (M4), native macOS, 660 GiB free disk. Homebrew LLVM 22.1.8 is already installed at `/opt/homebrew/opt/llvm` (keg-only; `clang`, `opt`, `llvm-config` from there are first on PATH, Apple's `/usr/bin/clang` is second). The user also has an existing `llvm-pass-skeleton` project that depends on this LLVM, so do not upgrade, remove, or relink it without asking first.
- Alive2 plan (verify, do not assume): Homebrew has an `alive2` formula (21.0, arm64 bottles; the formula page lists a dependency on a newer LLVM than 22.1.8, reportedly 23.x). Run `brew info alive2` and `brew deps alive2` first and report what it would install or upgrade. Preferred order: (a) `brew install alive2` and use the matching LLVM's `clang`/`opt` for the whole pipeline, if that does not disturb the existing LLVM 22; (b) otherwise build Alive2 from source against a compatible LLVM in a separate prefix; (c) if neither works natively, tell the user and propose a Linux container or lab machine. Textual IR can differ across LLVM versions, so the IR generator (`clang`/`opt`) and `alive-tv` MUST use the same LLVM version. Check this early with a smoke test.
- Use `alive-tv before.ll after.ll` on the (mutant, optimized mutant) pair; the Alive2 `opt` plugin is optional.
- Native macOS on Apple Silicon (decision: no Docker/VM). Use Homebrew `cmake ninja z3 re2c ccache` as needed. Apple's own clang has no `opt`, so use LLVM's tools (Homebrew `llvm`, keg-only, called by full path, or a source build). Always call tools by explicit path so the pipeline never picks up Apple's clang by accident.
- Pin ONE LLVM version that Alive2's current README supports and that builds on macOS. Check this first; it is the most likely early blocker. If Alive2 will not build natively, stop and tell me; the fallback is a Linux container or lab machine.
- Building LLVM is slow and large. Check free disk (`df -h /`) first. Prefer a Homebrew or prebuilt LLVM if it matches Alive2's requirement; otherwise Release build, assertions off, `-DLLVM_ENABLE_PROJECTS="clang;compiler-rt"` (compiler-rt for ASan/UBSan), minimal targets, and ccache.
- ASan and UBSan work on Apple Silicon; LeakSanitizer does not (not needed). IR targets `arm64-apple-macosx`; the report must state this.

## 7. Minimum viable deliverables (what "done" means)

| ID | Deliverable | Acceptance test |
|----|-------------|-----------------|
| D1 | Working toolchain (clang, opt, Alive2) in a script/Dockerfile | `scripts/setup.sh` reproduces it; Alive2 verifies a known-good and a known-bad transformation |
| D2 | Seed corpus, >= 20 programs (>= 6 per check class) | Each compiles to IR, has a guard, and has test inputs that trigger the guard |
| D3 | Baseline driver | Runs every seed through each pass and -O2/-O3; prints guard-count before/after |
| D4 | Mutator with >= 4 operators + UB filter | Produces valid IR (passes `opt -verify`); filter rejects mutants that add poison/undef flags (e.g., nsw/nuw/inbounds/nonnull) on guard computations |
| D5 | Differential harness | Runs O0 vs optimized builds under ASan+UBSan on seed inputs; logs divergences |
| D6 | Alive2 triage | Every candidate gets a classification label from section 4 |
| D7 | Results + report | results.csv, per-pass/per-pattern table, >= 2 written case studies |

Mutation operators (pick >= 4): flip/relax comparison predicate (ult<->ule, slt<->sle), change bound constant by +-1, change index width/sign-extension, reorder check and use (check-after-use), replace explicit check with overflow-intrinsic form, split a compound guard.

## 8. Schedule (compressed)

| Dates | Target | Needed for |
|-------|--------|-----------|
| Oct 27-29 | D1 toolchain working | |
| Oct 29-Nov 1 | D2 seeds (>= 20), D3 baseline driver | |
| Nov 2-3 | First 1-2 mutation operators + a first Alive2 run on baseline seeds; write interim report sections 4-5 with real numbers | **Interim report** |
| Nov 4-9 | D4 full mutator + UB filter, D5 harness | |
| Nov 10-14 | Scale run (target thousands of mutants), D6 triage | |
| Nov 15-17 | Aggregate metrics, minimize interesting cases | |
| Nov 18-20 | Case studies, final report, README cleanup | **Final** |

## 9. If you fall behind, cut in this order

1. Drop GVN (keep InstCombine + SimplifyCFG).
2. Drop the overflow-guard class (keep bounds + null).
3. Reduce operators to 3 and seeds to 15.
4. Never cut: Alive2 triage, the UB filter, or honest metrics. Those are the project's contribution.

## 10. Risks

- Alive2/LLVM version mismatch or slow build (mitigate: decide the pin on day 1; use a prebuilt LLVM if needed).
- Almost every flagged case is `LEGAL_UB` (this is a valid finding, not a failure: report the rates).
- Clang at -O0 marks functions `optnone`, which blocks passes; use `-Xclang -disable-O0-optnone` or emit with `-O1 -Xclang -disable-llvm-passes`.
- Mutants with UB make results meaningless; the UB filter and a sanitizer-clean check on the *unmutated* seed are the safeguard.

## 11. Ethics and safety

Only our own locally built open-source LLVM and our own seed programs are tested. No third-party systems. No credentials or keys in the repo. Any real miscompilation is documented, minimized, and (optionally) reported through LLVM's normal public issue tracker.