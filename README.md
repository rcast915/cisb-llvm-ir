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
- Seed IR is emitted with `$CLANG_IRFLAGS` = `-O1 -Xclang -disable-llvm-passes -fno-strict-aliasing`: no `optnone`, and no `!tbaa` metadata (Alive2 v21 fails with "Unsupported metadata: 1" on `!tbaa`). Consequence: TBAA-driven optimizations are not exercised.
- `alive-tv` exits 0 even when a transformation does not verify; the classifier must parse its output text.
- macOS has no `timeout`; `scripts/env.sh` defines `tmo SECONDS cmd...` (exit 142 on timeout).

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
| M2 seed corpus | — | next |
| M3 baseline driver | — | |
| M4 mutator (2 ops) + UB filter + first Alive2 run | — | |
| M5 remaining ops, ASan/UBSan harness, classification | — | |
| M6 aggregation + case studies | — | |

### M1 self-tests ([validate/m1/](validate/m1/))
- `good.ll`: `x*2 → x<<1`, must verify.
- `bad.ll`: wrap guard `x+1 > x → true` without `nsw`, must be rejected (counterexample x = INT_MAX).
- `ub_legal.ll`: same fold with `nsw`, must verify (the LEGAL_UB pattern); also checks InstCombine really does this fold.
- `roundtrip.c`: clang-23 IR → `opt -passes=sroa,instcombine` → `alive-tv before.ll after.ll`, must verify.
- `san_smoke.c`: clean run silent; ASan reports heap-buffer-overflow; UBSan reports signed overflow.
