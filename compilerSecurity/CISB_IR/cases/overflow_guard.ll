; Security property: detect signed addition overflow before accepting the result.
; The llvm.sadd.with.overflow intrinsic returns both the modular result and a flag.
source_filename = "overflow_guard.ll"

declare { i32, i1 } @llvm.sadd.with.overflow.i32(i32, i32)

define i32 @checked_add(i32 %a, i32 %b) {
entry:
  %pair = call { i32, i1 } @llvm.sadd.with.overflow.i32(i32 %a, i32 %b)
  %sum = extractvalue { i32, i1 } %pair, 0
  %overflow = extractvalue { i32, i1 } %pair, 1
  %valid = xor i1 %overflow, true
  ; CISB_GUARD: overflow
  br i1 %valid, label %safe, label %reject
safe:
  ret i32 %sum
reject:
  ret i32 -1
}

define i32 @main() {
entry:
  ; CISB_MUTATION_POINT: overflow_call
  %r = call i32 @checked_add(i32 2147483647, i32 1)
  ret i32 %r
}
