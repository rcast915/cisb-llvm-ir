#!/usr/bin/env bash
# Reproduce the toolchain natively on Apple Silicon macOS with Homebrew.
# Pinned versions (verified 2026-10-27):
#   Homebrew llvm 23.1.4 (pinned with `brew pin llvm`) -> clang, opt, llvm-as/dis
#   Homebrew alive2 21.0_9 = Alive2 tag v21.0 (913e155) + Homebrew backport
#     patches for LLVM 22 (a86aaa0) and LLVM 23 (155386f). Its bottle was
#     compiled against LLVM 23.1.3 headers and loads libLLVM.23.1.dylib (23.1.4)
#     at runtime, so `alive-tv --version` prints "LLVM version 23.1.3".
#   z3 5.3.2 (alive2 dependency)
# Usage: scripts/setup.sh   (installs if missing, verifies, runs M1 self-test)
set -euo pipefail
cd "$(dirname "$0")/.."
export HOMEBREW_NO_AUTO_UPDATE=1
source scripts/env.sh

brew list --versions alive2 >/dev/null || brew install alive2
brew list --pinned | grep -qx llvm || brew pin llvm

have_llvm=$("$LLVM_PREFIX/bin/llvm-config" --version)
have_alive=$(brew list --versions alive2 | awk '{print $2}')
[ "$have_llvm" = "$EXPECT_LLVM" ]   || { echo "LLVM is $have_llvm, expected $EXPECT_LLVM"; exit 1; }
[ "$have_alive" = "$EXPECT_ALIVE2" ] || { echo "alive2 is $have_alive, expected $EXPECT_ALIVE2"; exit 1; }

{
  echo "date: $(date -u +%FT%TZ)"
  echo "host: $(uname -sm) $(sw_vers -productVersion)"
  echo "clang: $(realpath "$CLANG") | $("$CLANG" --version | head -1)"
  echo "opt: $(realpath "$OPT") | $("$OPT" --version | grep -m1 version | xargs)"
  echo "alive-tv: $(realpath "$ALIVE_TV") | brew alive2 $have_alive | $("$ALIVE_TV" --version | head -1 | xargs) (banner from build headers)"
  echo "alive-tv loads: $(DYLD_PRINT_LIBRARIES=1 "$ALIVE_TV" --version 2>&1 | grep -o '/opt/homebrew/Cellar/llvm/[^ ]*libLLVM[^ ]*')"
  echo "sdk: $SDKROOT ($(xcrun --show-sdk-version))"
  echo "z3: $(brew list --versions z3)"
  echo "python: $(python3 --version)"
} | tee results/versions.txt

bash validate/m1/run_m1.sh
bash validate/m1/run_sanitizers.sh
