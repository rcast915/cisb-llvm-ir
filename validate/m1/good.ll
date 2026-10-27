; Known-correct: x * 2  ==>  x << 1
define i32 @src(i32 %x) {
  %r = mul i32 %x, 2
  ret i32 %r
}
define i32 @tgt(i32 %x) {
  %r = shl i32 %x, 1
  ret i32 %r
}
