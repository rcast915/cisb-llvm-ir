"""Unit tests for the guard counter, mutator/UB filter and IR UB monitor (no LLVM tools needed)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "driver"), str(ROOT / "mutator")]
import irguards  # noqa: E402
import mutate  # noqa: E402
import ubmon  # noqa: E402

GUARDED = """define i32 @f(i32 %x, i32 %n) {
entry:
  %a = add nsw i32 %x, 1
  %c = icmp ult i32 %x, %n
  br i1 %c, label %ok, label %bad
bad:
  call void @cisb_guard_fail(i32 7)
  ret i32 -1
ok:
  %d = icmp sgt i32 %a, 10
  br i1 %d, label %bad2, label %out
bad2:
  call void @cisb_guard_fail(i32 noundef 8)
  ret i32 -2
dead:
  call void @cisb_guard_fail(i32 9)
  ret i32 -3
out:
  ret i32 %a
}
"""


class GuardCounter(unittest.TestCase):
    def test_conditional_reachable_guards_only(self):
        self.assertEqual(irguards.count_ids(GUARDED), [7, 8])

    def test_constant_folded_branch_is_removed(self):
        folded = GUARDED.replace("br i1 %c, label %ok", "br i1 true, label %ok")
        self.assertEqual(irguards.count_ids(folded), [8])

    def test_phi_merged_marker_ids(self):
        t = """define void @g(i1 %c) {
  br i1 %c, label %2, label %3
2:
  %m = phi i32 [ 4, %1 ]
  call void @cisb_guard_fail(i32 %m)
  br label %3
3:
  ret void
}"""
        self.assertEqual(irguards.count_ids(t), [4])


class Mutator(unittest.TestCase):
    def test_operators_on_guard_icmps(self):
        got = sorted((op, after) for op, _, _, _, after, _ in mutate.mutants(GUARDED))
        self.assertEqual(got, [("const_pm1", "%d = icmp sgt i32 %a, 11"), ("const_pm1", "%d = icmp sgt i32 %a, 9"),
                               ("pred_flip", "%c = icmp ule i32 %x, %n"), ("pred_flip", "%d = icmp sge i32 %a, 10")])

    def test_all_generated_mutants_pass_static_filter(self):
        for *_, text in mutate.mutants(GUARDED):
            self.assertIsNone(mutate.static_ub_filter(GUARDED, text))

    def test_filter_rejects_added_poison_flag(self):
        bad = GUARDED.replace("%c = icmp ult i32 %x, %n", "%c = icmp samesign ult i32 %x, %n")
        self.assertIn("flag-tokens-changed", mutate.static_ub_filter(GUARDED, bad))

    def test_filter_rejects_non_icmp_and_multi_line_edits(self):
        self.assertEqual(mutate.static_ub_filter(GUARDED, GUARDED.replace("add nsw", "add nuw nsw")),
                         "changed-line-not-icmp")
        two = GUARDED.replace("icmp ult", "icmp ule").replace("icmp sgt", "icmp sge")
        self.assertEqual(mutate.static_ub_filter(GUARDED, two), "2-lines-changed")


class UBMonitor(unittest.TestCase):
    def test_instruments_nsw_add_and_asan_attribute(self):
        text = GUARDED + "\nattributes #0 = { nounwind }\n"
        out, kinds = ubmon.instrument(text)
        self.assertEqual(list(kinds.values()), ["signed-add-overflow"])
        self.assertIn("@llvm.sadd.with.overflow.i32(i32 %x, i32 1)", out)
        self.assertIn("declare void @cisb_ub(i1, i32)", out)
        self.assertIn("attributes #0 = { sanitize_address nounwind }", out)


if __name__ == "__main__":
    unittest.main()
