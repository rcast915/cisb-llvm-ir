# Contributing

Keep the first milestone small, reproducible, and conservative.

## Adding a seed or mutator

1. Add a minimal, standalone `.ll` seed and document its protected property.
2. Add exactly one `CISB_MUTATION_POINT:` marker before the call whose test inputs may be varied.
3. For each variant, document the preconditions that keep the reference execution defined. Do not use signed `add nsw` as an overflow test; prefer the appropriate `llvm.*with.overflow` intrinsic or explicitly bounded inputs.
4. Add a unit test for the expected variant count and any guard-shape behavior.
5. Run the Python tests and compile/run each new seed and generated variant with the chosen LLVM/Clang installation, optionally with ASan/UBSan.
6. Record LLVM and Alive2 versions and retain a minimized reproducer for every candidate.
7. Treat IR-shape changes as heuristics. Do not call a result a compiler bug until the reference semantics, optimized behavior, and validation evidence have been reviewed.

## Pull request checklist

- [ ] Reproducer and mutation metadata are deterministic.
- [ ] Reference inputs stay within documented defined-behavior invariants.
- [ ] Unit tests pass.
- [ ] Any candidate includes original IR, optimized IR, tool versions, exact commands, and triage status.
- [ ] No private artifacts or sensitive information are included.
