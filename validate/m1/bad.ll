; Known-incorrect: wrap guard "x + 1 > x" folded to true WITHOUT nsw.
; Wrong for x = INT_MAX (x + 1 wraps to INT_MIN).
define i1 @src(i32 %x) {
  %a = add i32 %x, 1
  %c = icmp sgt i32 %a, %x
  ret i1 %c
}
define i1 @tgt(i32 %x) {
  ret i1 true
}
