from __future__ import annotations

import unittest
from pathlib import Path

from cisb_hunter.analysis import compare_guard_shapes, guard_summary
from cisb_hunter.mutations import generate
from cisb_hunter.runner import classify_alive2, executions_differ

ROOT = Path(__file__).resolve().parents[1]


class GuardSummaryTests(unittest.TestCase):
    def test_counts_security_guard_patterns(self) -> None:
        ir = """
        %x = icmp ult i64 %idx, %len
        %p = icmp ne ptr %raw, null
        %q = call { i32, i1 } @llvm.sadd.with.overflow.i32(i32 %a, i32 %b)
        br i1 %x, label %ok, label %bad
        """
        got = guard_summary(ir)
        self.assertEqual(got["conditional_branches"], 1)
        self.assertEqual(got["integer_range_comparisons"], 1)
        self.assertEqual(got["pointer_null_comparisons"], 1)
        self.assertEqual(got["overflow_intrinsics"], 1)

    def test_reduction_is_review_signal_not_proof(self) -> None:
        before = "%c = icmp ult i64 %i, %n\nbr i1 %c, label %ok, label %bad\n"
        after = "br label %ok\n"
        result = compare_guard_shapes(before, after)
        self.assertTrue(result["review_recommended"])
        self.assertIn("integer_range_comparisons", result["reductions"])

    def test_alive2_output_classification(self) -> None:
        self.assertEqual(classify_alive2("Transformation seems to be correct!", 0), "proven_correct")
        self.assertEqual(classify_alive2("Transformation doesn't verify", 0), "counterexample_or_unsound")

    def test_execution_comparison_uses_exit_status_and_stdout(self) -> None:
        self.assertFalse(executions_differ({"returncode": 0, "stdout": "ok"}, {"returncode": 0, "stdout": "ok"}))
        self.assertTrue(executions_differ({"returncode": 0, "stdout": "ok"}, {"returncode": 1, "stdout": "ok"}))

    def test_all_seed_ir_files_have_mutation_marker(self) -> None:
        for path in (ROOT / "cases").glob("*.ll"):
            text = path.read_text(encoding="utf-8")
            self.assertEqual(text.count("CISB_MUTATION_POINT:"), 1, path.name)
            self.assertIn("define i32 @main()", text, path.name)

    def test_safe_variant_generator_creates_expected_count(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "generated"
            written = generate(ROOT / "cases", output)
            self.assertEqual(len(written), 11)
            for path in written:
                self.assertTrue(path.is_file())
                self.assertIn("CISB_MUTATION_POINT:", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
