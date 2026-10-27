# CISB detection via LLVM IR mutation + Alive2

Course project (CS 5352/6362). Scope, definitions and schedule: [project_scope.md](project_scope.md).

## Toolchain (pinned, native macOS on Apple Silicon)

| Tool | Version | Path |
|------|---------|------|
| clang / opt / llvm-as / llvm-dis | Homebrew `llvm` **23.1.4** (`brew pin llvm`) | `/opt/homebrew/opt/llvm/bin/` |
| alive-tv | Homebrew `alive2` **21.0_9** = Alive2 tag `v21.0` (913e155) + Homebrew backports a86aaa0 (LLVM 22) and 155386f (LLVM 23) | `/opt/homebrew/opt/alive2/bin/alive-tv` |
| z3 | 5.3.2 | Homebrew |
| SDK | Xcode MacOSX.sdk (27.0) | `xcrun --show-sdk-path` |

All IR targets `arm64-apple-macosx26.0.0`.

Notes:
- `alive-tv --version` prints "LLVM version 23.1.3": that string is compiled into the Homebrew bottle from the headers it was built with. At runtime it loads `/opt/homebrew/Cellar/llvm/23.1.4/lib/libLLVM.23.1.dylib`, the same library `opt` uses (checked with `DYLD_PRINT_LIBRARIES`).
- Homebrew clang's per-target config (`/opt/homebrew/etc/clang/arm64-apple-macosx26.cfg`) points at a missing SDK, so every clang call uses `$CLANG_SYSFLAGS` (`--no-default-config -isysroot $SDKROOT`).
- Seed IR is emitted with `$CLANG_IRFLAGS` = `-O1 -Xclang -disable-llvm-passes -Xclang -disable-lifetime-markers -fno-strict-aliasing`, so functions carry no `optnone` and passes really run.
- `alive-tv` exits 0 even when a transformation does not verify; the classifier must parse its output text.
- macOS has no `timeout`; `scripts/env.sh` defines `tmo SECONDS cmd...` (exit 142 on timeout).

## Limitations (state these in the report)

- **No TBAA (`-fno-strict-aliasing`).** Alive2 v21 rejects `!tbaa` metadata ("Unsupported metadata: 1"), so seeds are compiled without it. Optimizations that rely on type-based alias analysis are not exercised. Any remaining Alive2 failure on unsupported features is labelled `UNKNOWN` with a sub-label (e.g. `UNKNOWN:unsupported-metadata`) and counted separately.
- **No lifetime markers (`-Xclang -disable-lifetime-markers`).** LLVM 23's one-argument `llvm.lifetime.start/end` is "Unsupported instruction" in Alive2 v21. The markers only describe stack-slot liveness and `sroa` deletes them for promoted locals, but stack-coloring style optimizations are not exercised.
- **O2/O3 output is mostly not checkable by Alive2 v21.** `default<O2|O3>` infers parameter attributes that Alive2 v21 rejects (`nofree`, `captures(address_is_null)`, `captures(address)`); those rows are `UNKNOWN:unsupported-attribute:<attr>`. Isolated-pass rows are unaffected.
- **Guard marker.** Each guard's error path calls an external `cisb_guard_fail(id)` so guards can be counted in IR and seen at run time. Real code often just returns an error code; the opaque call can block some transformations (e.g. turning the guard into a `select`).
- **Loops.** Alive2 checks loops only up to a bounded unroll; each looping seed records its bound in `inputs.json` (`alive2_unroll`), and results are only valid up to that bound.
- Target is `arm64-apple-macosx26.0.0` only.

## Setup

```sh
scripts/setup.sh        # installs alive2 if missing, pins llvm, checks versions, runs M1 self-tests
source scripts/env.sh   # in bash: $CLANG $OPT $ALIVE_TV $CLANG_SYSFLAGS $CLANG_IRFLAGS, tmo
```

Versions are written to `results/versions.txt`; the full M1 log is `results/m1_log.txt`.

## Stages

| Milestone | How to run | Status |
|-----------|-----------|--------|
| M1 toolchain | `scripts/setup.sh` | **done** (2026-10-27) |
| M2 seed corpus | `scripts/check_seeds.sh` | **done** (2026-10-27): 31 seeds, all checks pass |
| M3 baseline driver | `scripts/run_baseline.sh` then `python3 driver/summarize_baseline.py` | **done** (2026-10-27); Arm B gate: 2 bounds controls show no change (see below) |
| M4 mutator (2 ops) + UB filter + first Alive2 run | — | next |
| M5 remaining ops, ASan/UBSan harness, classification | — | |
| M6 aggregation + case studies | — | |

### M1 self-tests ([validate/m1/](validate/m1/))
- `good.ll`: `x*2 → x<<1`, must verify.
- `bad.ll`: wrap guard `x+1 > x → true` without `nsw`, must be rejected (counterexample x = INT_MAX).
- `ub_legal.ll`: same fold with `nsw`, must verify (the LEGAL_UB pattern); also checks InstCombine really does this fold.
- `roundtrip.c`: clang-23 IR → `opt -passes=sroa,instcombine` → `alive-tv before.ll after.ll`, must verify.
- `san_smoke.c`: clean run silent; ASan reports heap-buffer-overflow; UBSan reports signed overflow.

## Experiment arms (scope doc section 4b)

Every seed, mutant and results row carries `arm`; the arms are never mixed in one headline number.

- **Arm A, UB-free hunt (23 seeds).** Must be sanitizer-clean on every input. Mutants get the strict UB filter and are re-checked sanitizer-clean.
- **Arm B, positive controls (8 seeds, `ub_by_construction`).** Classic CISB patterns that are UB in C. Exempt from the sanitizer-clean rule; the expected `-O0` ASan/UBSan behaviour is recorded per input (`expect_reports`, `expect_guard_output`) and checked.

## Seed corpus ([seeds/](seeds/))

Each seed is `seeds/<id>/seed.c` + `inputs.json` (arm, class, `ub_pattern` for Arm B, functions, guard ids, loop/unroll bound, inputs with `guard: pass|trip` and expected sanitizer reports). `main` is only compiled with `-DSEED_MAIN`, so the seed IR contains just the guarded function(s). Shared support: [seeds/common/](seeds/common/).

`scripts/check_seeds.sh` checks, per seed:
- the IR compiles, passes `opt -passes=verify`, and no function has `optnone`;
- every expected guard id is found as a conditional guard ([driver/irguards.py](driver/irguards.py));
- every input runs correctly in an `-O0 -fsanitize=address,undefined` build, by the rules of its arm.

Outputs: `results/m2_seeds.csv` (per seed), `results/m2_inputs.csv` (per input: observed GUARD line, sanitizer reports, exit code), `results/m2_commands.txt` (exact commands), `results/m2_log.txt`.

| Seed | Arm | Class | Guard ids | Loops (Alive2 unroll) | Inputs (trip) | Pattern |
|---|---|---|---|---|---|---|
| `a_bnd01_idx_unsigned` | A | bounds | 1 | no | 5 (3) | unsigned index i >= n |
| `a_bnd02_idx_signed` | A | bounds | 2 | no | 5 (3) | signed index i < 0 || i >= n (compound guard) |
| `a_bnd03_fixed_buf` | A | bounds | 3 | no | 4 (2) | store into global int[16], idx > 15 |
| `a_bnd04_memcpy_range` | A | bounds | 4 | no | 5 (3) | overflow-safe range check off > cap || len > cap - off before memcpy |
| `a_bnd05_loop_copy` | A | bounds | 5 | yes (8) | 5 (2) | in-loop guard i >= dst_len while copying n words |
| `a_bnd06_mask_index` | A | bounds | 6 | no | 4 (2) | power-of-two ring, reject idx with bits outside mask |
| `a_bnd07_char_at` | A | bounds | 7 | no | 4 (2) | string position pos >= len |
| `a_bnd08_matrix` | A | bounds | 8 | no | 5 (3) | 2-D bounds r >= rows || c >= cols |
| `a_nul01_ptr_param` | A | null | 21 | no | 2 (1) | if (!p) before *p |
| `a_nul02_struct_field` | A | null | 22 | no | 3 (2) | !b || !b->data before b->data[0] |
| `a_nul03_lookup` | A | null | 23 | yes (4) | 4 (2) | result of table lookup checked for NULL |
| `a_nul04_list_walk` | A | null | 24 | yes (5) | 4 (2) | walk n && n->val != k, then !n |
| `a_nul05_callback` | A | null | 25 | no | 2 (1) | NULL function pointer check before indirect call |
| `a_nul06_out_param` | A | null | 26 | no | 2 (1) | NULL out-parameter check before store |
| `a_nul07_safe_strlen` | A | null | 27 | yes (6) | 3 (1) | NULL string check before length loop |
| `a_ovf01_uadd_wrap` | A | overflow | 11 | no | 4 (2) | unsigned wrap check s = a + b; s < a (defined behaviour) |
| `a_ovf02_sadd_precheck` | A | overflow | 12 | no | 4 (2) | signed add pre-check against INT_MAX - b / INT_MIN - b |
| `a_ovf03_mul_alloc` | A | overflow | 13 | no | 4 (2) | calloc-style n * sz overflow check n > SIZE_MAX / sz |
| `a_ovf04_builtin_add` | A | overflow | 14 | no | 4 (2) | __builtin_add_overflow (llvm.sadd.with.overflow) |
| `a_ovf05_len_header` | A | overflow | 15 | no | 4 (2) | len + HDR fits in uint32: len > UINT32_MAX - HDR |
| `a_ovf06_usub_underflow` | A | overflow | 16 | no | 4 (2) | unsigned underflow used > total |
| `a_ovf07_signed_len` | A | overflow | 17 | no | 4 (2) | signed length to size_t: len < 0 || len > cap |
| `a_ovf08_shift_amount` | A | overflow | 18 | no | 4 (2) | shift amount s >= 32 |
| `b_bnd01_read_then_check` | B | bounds | 37 | no | 2 (1) | bounds_check_after_use |
| `b_bnd02_loop_use_then_check` | B | bounds | 38 | yes (6) | 3 (1) | bounds_check_after_use |
| `b_nul01_deref_then_check` | B | null | 35 | no | 2 (1) | null_check_after_deref |
| `b_nul02_store_then_check` | B | null | 36 | no | 2 (1) | null_check_after_deref |
| `b_ovf01_sadd_check_after` | B | overflow | 31 | no | 2 (1) | signed_overflow_check_after_add |
| `b_ovf02_inc_wrap` | B | overflow | 32 | no | 2 (1) | signed_overflow_check_after_add |
| `b_ptr01_wrap_check` | B | bounds | 33 | no | 2 (1) | pointer_wrap_check |
| `b_ptr02_wrap_or_end` | B | bounds | 34 | no | 4 (2) | pointer_wrap_check |

## M3 baseline ([driver/run_baseline.py](driver/run_baseline.py))

Pipelines (exact `opt -passes=` strings are in the `opt_passes` column; the CSV's first line documents the setup):

| pipeline | `-passes=` |
|---|---|
| `sroa` | `sroa` (the prelude alone, a control) |
| `sroa+instcombine` | `sroa,instcombine` |
| `sroa+simplifycfg` | `sroa,simplifycfg` |
| `sroa+gvn` | `sroa,gvn` |
| `O2` / `O3` | `default<O2>` / `default<O3>` (no prelude) |

**Prelude:** isolated passes always run after `sroa` and nothing else, because clang's unoptimized IR keeps every local in memory and the three passes are meant to see SSA values.

Per (seed, pipeline) row in `results/baseline.csv`:
- **Guards:** ids before/after, counted with `driver/irguards.py` exactly as in M2. *Removed* = id no longer a conditional guard (branch gone or constant-folded). *Weakened* = id still in the IR, but an input that printed `GUARD id` at -O0 no longer does (so weakening is only detected on the recorded inputs).
- **Behavioural differential (plain builds, no sanitizers):** the unoptimized seed IR and the optimized IR are each compiled with `clang -O0` (codegen only, so only the IR pipeline differs) and linked with the same `main` (from `llvm-extract --delete`) and harness. Every input is run on both; exit code and `GUARD` lines are compared.
- **UB attribution:** a separate `-O0 -fsanitize=address,undefined` build of the source runs the same inputs. A divergence is `ub_attributed` if that build reported anything on the input. It is never used as the divergence oracle.
- **Alive2:** `alive-tv --smt-to=10000 [--src-unroll=N --tgt-unroll=N] seed.ll <pipeline>.ll`, 300 s process timeout. `alive2_verdict` is CORRECT / INCORRECT / UNKNOWN (with sub-label) / NO_TRANSFORM for every row.
- **Classification (candidates only, i.e. removed, weakened or divergent):** INCORRECT -> `MISCOMPILE`; UNKNOWN -> `UNKNOWN:<sub-label>`; CORRECT -> `LEGAL_UB` if the seed is `ub_by_construction` or sanitizers flagged an input, else `BENIGN`.

`driver/summarize_baseline.py` prints the per-arm tables to `results/baseline_summary.txt`. Logs/commands: `results/m3_log.txt`, `results/m3_commands.txt`.
