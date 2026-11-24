# Linux/Docker replacement for scripts/env.sh (bind-mounted over it). Same variable names.
export LLVM_PREFIX=/usr/lib/llvm-23
export CLANG=$LLVM_PREFIX/bin/clang
export OPT=$LLVM_PREFIX/bin/opt
export LLVM_AS=$LLVM_PREFIX/bin/llvm-as
export LLVM_DIS=$LLVM_PREFIX/bin/llvm-dis
export ALIVE_TV=/opt/alive2/build/alive-tv
export EXPECT_LLVM=23
export EXPECT_ALIVE2=v21.0+a86aaa0+155386f
tmo() { perl -e 'alarm shift; exec @ARGV or die "exec failed: $!\n"' "$@"; }
export CLANG_SYSFLAGS=""
export CLANG_IRFLAGS="-O1 -Xclang -disable-llvm-passes -Xclang -disable-lifetime-markers -fno-strict-aliasing -S -emit-llvm"
