"""Generate safe test-input variants for the three seed IR programs.

This is deliberately not a general-purpose textual LLVM IR mutator. Each
replacement is explicitly curated with an invariant that keeps the reference
program defined. In particular, bounds failures are rejected before the GEP
and load, and arithmetic overflow is handled by llvm.*with.overflow intrinsics.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

# (variant name, replacement for the LLVM IR call immediately after the marker)
VARIANTS: dict[str, list[tuple[str, str]]] = {
    "bounds_guard.ll": [
        ("valid_first_element", "%r = call i32 @checked_load(ptr %base, i64 0, i64 2)"),
        ("valid_last_element", "%r = call i32 @checked_load(ptr %base, i64 1, i64 2)"),
        ("reject_at_boundary", "%r = call i32 @checked_load(ptr %base, i64 2, i64 2)"),
        ("reject_beyond_boundary", "%r = call i32 @checked_load(ptr %base, i64 3, i64 2)"),
        ("reject_empty_logical_range", "%r = call i32 @checked_load(ptr %base, i64 0, i64 0)"),
    ],
    "overflow_guard.ll": [
        ("no_overflow", "%r = call i32 @checked_add(i32 10, i32 20)"),
        ("positive_overflow", "%r = call i32 @checked_add(i32 2147483647, i32 1)"),
        ("negative_overflow", "%r = call i32 @checked_add(i32 -2147483648, i32 -1)"),
        ("zero_inputs", "%r = call i32 @checked_add(i32 0, i32 0)"),
    ],
    "null_guard.ll": [
        ("reject_null", "%r = call i32 @checked_deref(ptr null)"),
        ("accept_valid_pointer", "%r = call i32 @checked_deref(ptr %cell)"),
    ],
}


def replace_marked_call(source: str, replacement: str) -> str:
    lines = source.splitlines()
    marker_indices = [i for i, line in enumerate(lines) if "CISB_MUTATION_POINT:" in line]
    if len(marker_indices) != 1:
        raise ValueError("Expected exactly one CISB_MUTATION_POINT marker per seed IR file")
    marker = marker_indices[0]
    target = marker + 1
    while target < len(lines) and (not lines[target].strip() or lines[target].lstrip().startswith(";")):
        target += 1
    if target >= len(lines) or "call i32 @checked_" not in lines[target]:
        raise ValueError("Mutation marker must be followed by a call to a checked_* function")
    indent = lines[target][: len(lines[target]) - len(lines[target].lstrip())]
    lines[target] = indent + replacement
    return "\n".join(lines) + "\n"


def generate(cases_dir: Path, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for seed_name, variants in VARIANTS.items():
        seed_path = cases_dir / seed_name
        if not seed_path.is_file():
            raise FileNotFoundError(f"Required seed is missing: {seed_path}")
        seed_text = seed_path.read_text(encoding="utf-8")
        for variant_name, replacement in variants:
            variant_text = replace_marked_call(seed_text, replacement)
            # A small invariant guard against accidentally mutating non-call code.
            if "CISB_MUTATION_POINT:" not in variant_text:
                raise AssertionError("Mutation marker unexpectedly disappeared")
            target_dir = output_dir / seed_path.stem
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / f"{variant_name}.ll"
            target.write_text(variant_text, encoding="utf-8")
            written.append(target)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=Path("cases"), help="Directory containing seed .ll files")
    parser.add_argument("--out", type=Path, default=Path("generated-cases"), help="Output directory for safe variants")
    args = parser.parse_args()
    try:
        paths = generate(args.cases, args.out)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f"Generated {len(paths)} safe test-input variants in {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
