; Security property: do not calculate/load the indexed element unless idx < len.
source_filename = "bounds_guard.ll"

define i32 @checked_load(ptr %base, i64 %idx, i64 %len) {
entry:
  %in_bounds = icmp ult i64 %idx, %len
  ; CISB_GUARD: bounds
  br i1 %in_bounds, label %load, label %reject
load:
  %address = getelementptr inbounds i32, ptr %base, i64 %idx
  %value = load i32, ptr %address, align 4
  ret i32 %value
reject:
  ret i32 -1
}

define i32 @main() {
entry:
  %buffer = alloca [2 x i32], align 4
  %p0 = getelementptr inbounds [2 x i32], ptr %buffer, i64 0, i64 0
  %p1 = getelementptr inbounds [2 x i32], ptr %buffer, i64 0, i64 1
  store i32 17, ptr %p0, align 4
  store i32 29, ptr %p1, align 4
  %base = getelementptr inbounds [2 x i32], ptr %buffer, i64 0, i64 0
  ; CISB_MUTATION_POINT: bounds_call
  %r = call i32 @checked_load(ptr %base, i64 2, i64 2)
  ret i32 %r
}
