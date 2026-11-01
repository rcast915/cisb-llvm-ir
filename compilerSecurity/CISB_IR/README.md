# Detecting Compiler-Introduced Security Bugs in LLVM IR Optimizations

**Status:** research starter / MVP scaffold. This repository is a reproducible test harness, not a claim that LLVM currently contains a vulnerability.

## Goal

Test whether a selected LLVM IR optimization pipeline changes security-relevant behavior in programs whose reference IR is well-defined for the tested inputs. The starter covers three guard classes: bounds checks, checked signed addition, and null-pointer checks. It combines LLVM IR verification, a selected pass pipeline, a small structural guard audit, native differential execution, optional ASan/UBSan instrumentation, and optional Alive2 translation validation.

## What is included

- `cases/`: three small, standalone LLVM IR programs with documented security properties.
- `cisb_hunter/runner.py`: verifies input IR, runs a configurable pipeline, saves optimized IR, compiles and executes both forms, performs structural audits, and invokes `alive-tv` if available.
- `cisb_hunter/mutations.py`: generates 11 curated input variants. Variant constraints keep the reference program defined: bounds checks reject invalid indices before memory access; the overflow intrinsic returns a result and flag rather than using signed `add nsw`; and the null-check function rejects null before the load.
- `cisb_hunter/analysis.py`: lightweight regex counters that flag selected guard-shape reductions for review. They are not a semantic proof.
- `tests/`: standard-library unit tests.
- `artifacts/`: created locally by runs; ignored by Git.

## Requirements

- Python 3.10 or newer. No pip packages are required.
- LLVM `opt` and Clang from compatible LLVM installations for optimization/compilation experiments. Opaque-pointer IR in the examples targets modern LLVM releases.
- Optional: `alive-tv` from [Alive2](https://github.com/AliveToolkit/alive2) for translation validation.

This is deliberately dependency-light, not literally compiler-free: Python-only tests and safe variant generation work without LLVM, but compiler experiments require the LLVM command-line tools. Keep `opt` and `clang` from the same LLVM release when possible.

## Quick start

Run from the repository root:

```bash
python3 --version
python3 -m unittest discover -s tests -v
python3 -m cisb_hunter.mutations --cases cases --out generated-cases
```

Then run the compiler pipeline after LLVM tools are installed and available on `PATH`:

```bash
python3 -m cisb_hunter \
  --cases generated-cases \
  --out artifacts/first-run \
  --passes instcombine,simplifycfg,gvn \
  --sanitizers none
```

Run with sanitizer instrumentation where the installed Clang distribution supports its sanitizer runtimes:

```bash
python3 -m cisb_hunter \
  --cases generated-cases \
  --out artifacts/sanitized-run \
  --passes instcombine,simplifycfg,gvn \
  --sanitizers address,undefined
```

If tool names differ, provide explicit paths:

```bash
python3 -m cisb_hunter --opt /path/to/opt --clang /path/to/clang \
  --alive-tv /path/to/alive-tv --cases generated-cases --out artifacts/alive2-run
```

For pass attribution, run each pass into a separate output directory and keep the combined pipeline as a separate experiment:

```bash
for pass in instcombine simplifycfg gvn; do
  python3 -m cisb_hunter --cases generated-cases \
    --out "artifacts/${pass}" --passes "$pass" --sanitizers none
 done
python3 -m cisb_hunter --cases generated-cases \
  --out artifacts/combined --passes instcombine,simplifycfg,gvn --sanitizers none
```

The same pipeline can be run with `-verify-each` enabled by the harness to catch invalid intermediate IR. The exact pass pipeline syntax follows LLVM's new pass manager; see the [LLVM `opt` command guide](https://llvm.org/docs/CommandGuide/opt.html).

## Reading results

Each run writes:

- `summary.md`: compact per-case status table.
- `summary.json`: machine-readable full result, command timings and error tails.
- `tools.json`: paths and versions of the tools selected.
- `<case>/optimized.ll`: transformed IR.
- `<case>/alive2.log`: raw Alive2 output if `alive-tv` was available.

Interpretation is intentionally conservative:

- `candidate_runtime_divergence`: exit status or standard output changed.
- `high_priority_candidate_optimized_only_sanitizer_report`: sanitizer reported an error only for optimized execution.
- `review_guard_shape_change`: tracked guard-like pattern counts decreased.
- `review_alive2_counterexample`: Alive2 output appears to report a counterexample/unsound transformation.
- `no_signal_in_this_run`: none of these simple signals triggered; **not** proof of correctness.

A structural count decrease is only a review lead. Legitimate optimization can remove redundant checks when the IR semantics proves them unnecessary. Conversely, the regex audit can miss guard changes that use different IR patterns. Confirm candidates with a minimized reproducer, per-pass testing, LLVM verifier output, Alive2 where supported, and careful semantic review.

## Mutation policy

`mutations.py` does not rewrite comparison operators or inject unguarded loads. It changes only the marked call arguments in the three curated templates. The allowed variants and invariants are explicit in code. If the team adds a mutator, require it to document:

1. The IR-level preconditions and parameter ranges.
2. Why each generated reference case is defined for those parameters.
3. An independent invariant/test that rejects unsafe generated cases.
4. A seed and serialized metadata so each result is reproducible.

A deliberately unsafe fault-injection mode may be useful later for validating the detector, but its output should be stored and reported separately from the defined-reference corpus.

## Proposed one-month plan

| Week | Deliverable | Acceptance criterion |
|---|---|---|
| 1 | Run harness, curated cases, reproducible JSON, safe variant generator | All unit tests pass; seed IR verifies and compiles on the selected LLVM toolchain |
| 2 | Add per-pass sweep and more guard patterns/mutators | Every variant records its source seed, inputs, pass, tool versions and outcome |
| 3 | Add Alive2 triage, deduplication and manual candidate validation | Each candidate has a minimized reproducer and a recorded validator result/limitation |
| 4 | Batch evaluation and final report | Report yield, confirmation rate, false-positive accounting, runtime and validation overhead |

## Evaluation protocol

Pre-register the seed corpus and all pass pipelines. For each case, record the LLVM/Clang/Alive2 versions, exact command lines, timeout, sanitizer configuration, wall time, source and transformed IR. Run each pass independently (`instcombine`, `simplifycfg`, `gvn`) and as a combined pipeline. Keep a separate fault-injection corpus for measuring whether the harness detects known guard-removal controls. Manually triage every signal; count a true positive only when the candidate is minimized and independently supported by semantic validation or an equivalent compelling proof. Count false positives among signals shown to be semantics-preserving. Report number of cases, signal yield, confirmed findings, false-positive proportion among reviewed signals, time per case, timeout/unknown rate, and Alive2 overhead. Do not claim meaningful statistical generalization from this small seed suite.

## Known limitations / next steps

1. Runtime tests execute only each fixture's `main()` path; extend to generated input coverage before making yield claims.
2. The regex audit is a deliberately small heuristic, not a full CFG or dataflow analysis.
3. UBSan/ASan coverage depends on how the installed Clang instruments and links externally supplied IR; absence of a report is weak evidence.
4. Alive2 has a bounded supported semantics and known limitations, including interprocedural transformations. It should not be interpreted as a whole-program proof for unsupported pass behavior.
5. Run only locally or in authorized CI environments. Do not publish private compiler crash data or sensitive information.

## References

- LLVM Project, [`opt` command guide](https://llvm.org/docs/CommandGuide/opt.html).
- LLVM Project, [Using the New Pass Manager](https://llvm.org/docs/NewPassManager.html).
- AliveToolkit, [Alive2 README and `alive-tv` usage](https://github.com/AliveToolkit/alive2).
- LLVM Project, [AddressSanitizer](https://clang.llvm.org/docs/AddressSanitizer.html).
- LLVM Project, [UndefinedBehaviorSanitizer](https://clang.llvm.org/docs/UndefinedBehaviorSanitizer.html).

## Optional Docker setup

The Dockerfile installs Python and a matched LLVM 18 `opt`/Clang toolchain, so users do not need to install Python packages or configure LLVM locally. Docker is optional; using a host installation of compatible LLVM tools works too.

```bash
docker build -t cisb-ir .
# Generate the curated variants in the shared project directory.
docker run --rm --entrypoint python3 -v "$PWD:/workspace" -w /workspace cisb-ir \
  -m cisb_hunter.mutations --cases cases --out generated-cases
# Run optimization and differential execution. Results are written to the mounted workspace.
docker run --rm -v "$PWD:/workspace" -w /workspace cisb-ir \
  --cases generated-cases --out artifacts/docker-run \
  --passes instcombine,simplifycfg,gvn --sanitizers address,undefined
```

The Docker image does not include Alive2; use `--alive-tv /path/to/alive-tv` in a host run or extend the image with a compatible Alive2 build when the team is ready for translation validation. The LLVM/Clang packages in Ubuntu 24.04 include LLVM 18, which is available in the official package archive [LLVM 18 package](https://packages.ubuntu.com/noble/llvm-18), [Clang 18 package](https://packages.ubuntu.com/noble/clang-18).
