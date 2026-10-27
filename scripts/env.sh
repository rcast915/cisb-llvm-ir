# Source this: pinned tool paths. Always use these, never bare `clang`/`opt`.
export LLVM_PREFIX=/opt/homebrew/opt/llvm
export CLANG=$LLVM_PREFIX/bin/clang
export OPT=$LLVM_PREFIX/bin/opt
export LLVM_AS=$LLVM_PREFIX/bin/llvm-as
export LLVM_DIS=$LLVM_PREFIX/bin/llvm-dis
export ALIVE_TV=/opt/homebrew/opt/alive2/bin/alive-tv
export EXPECT_LLVM=23.1.4
export EXPECT_ALIVE2=21.0_9
# tmo SECONDS cmd...  -- run with a hard timeout (macOS has no `timeout`). Exit 142 = timed out.
tmo() { perl -e 'alarm shift; exec @ARGV or die "exec failed: $!\n"' "$@"; }
# Homebrew clang's default sysroot (MacOSX26.sdk under CommandLineTools) is missing here; use Xcode's SDK.
export SDKROOT=${SDKROOT:-$(xcrun --show-sdk-path)}
# Pass on every clang call: ignore Homebrew's per-target .cfg (its macosx26 cfg names a missing SDK).
export CLANG_SYSFLAGS="--no-default-config -isysroot $SDKROOT"
# Standard flags for emitting seed IR: passes not skipped (no optnone), and no !tbaa
# metadata (Alive2 v21 reports "Unsupported metadata: 1" on !tbaa).
export CLANG_IRFLAGS="-O1 -Xclang -disable-llvm-passes -fno-strict-aliasing -S -emit-llvm"
