; Security property: never dereference a null pointer.
source_filename = "null_guard.ll"

define i32 @checked_deref(ptr %p) {
entry:
  %not_null = icmp ne ptr %p, null
  ; CISB_GUARD: null
  br i1 %not_null, label %load, label %reject
load:
  %value = load i32, ptr %p, align 4
  ret i32 %value
reject:
  ret i32 -1
}

define i32 @main() {
entry:
  %cell = alloca i32, align 4
  store i32 23, ptr %cell, align 4
  ; CISB_MUTATION_POINT: null_call
  %r = call i32 @checked_deref(ptr null)
  ret i32 %r
}
