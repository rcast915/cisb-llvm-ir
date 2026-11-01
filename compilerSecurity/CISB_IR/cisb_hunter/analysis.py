"""Lightweight, intentionally conservative IR-shape heuristics.

These heuristics flag review-worthy structural changes; they do not prove that
an optimization is incorrect. Use Alive2 and minimized counterexamples for
semantic validation.
"""
from __future__ import annotations

import re
from typing import Any


def guard_summary(ir_text: str) -> dict[str, int]:
    """Count selected guard-like IR constructs using version-tolerant regexes."""
    return {
        "conditional_branches": len(re.findall(r"(?m)^\s*br\s+i1\b", ir_text)),
        "integer_range_comparisons": len(
            re.findall(r"\bicmp\s+(?:u(?:lt|le|gt|ge)|s(?:lt|le|gt|ge))\s+i\d+\b", ir_text)
        ),
        "pointer_null_comparisons": len(
            re.findall(r"\bicmp\s+(?:eq|ne)\s+ptr\b[^\n]*\bnull\b", ir_text)
        ),
        "overflow_intrinsics": len(
            re.findall(r"\bcall\s+\{[^}]+\}\s+@llvm\.[su](?:add|sub|mul)\.with\.overflow\.i\d+\b", ir_text)
        ),
    }


def compare_guard_shapes(original_ir: str, optimized_ir: str) -> dict[str, Any]:
    """Return counts and reductions that merit triage, not bug verdicts."""
    before = guard_summary(original_ir)
    after = guard_summary(optimized_ir)
    reductions = {
        key: {"before": before[key], "after": after[key], "removed": before[key] - after[key]}
        for key in before
        if before[key] > after[key]
    }
    return {
        "before": before,
        "after": after,
        "reductions": reductions,
        "review_recommended": bool(reductions),
        "interpretation": (
            "A pattern count decreased; inspect the diff and prove whether the removed "
            "check was redundant under LLVM semantics. This heuristic is not a correctness proof."
            if reductions
            else "No tracked guard-like pattern count decreased; this does not establish correctness."
        ),
    }
