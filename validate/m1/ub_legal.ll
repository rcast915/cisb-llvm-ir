; Same fold, but the add carries nsw: overflow is poison, so the fold is a
; valid refinement. This is the LEGAL_UB pattern the pipeline must label.
define i1 @src(i32 %x) {
  %a = add nsw i32 %x, 1
  %c = icmp sgt i32 %a, %x
  ret i1 %c
}
define i1 @tgt(i32 %x) {
  ret i1 true
}
