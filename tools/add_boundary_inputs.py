#!/usr/bin/env python3
"""Append boundary-value inputs to existing seeds' inputs.json (extended corpus only).
Usage: add_boundary_inputs.py <repo>/seeds
Each new input is tagged "boundary": true so it can be told apart from the original inputs."""
import json
import sys
from pathlib import Path

P, T = "pass", "trip"
NEW = {  # seed -> [(args, guard, expected sanitizer reports, note)]
    "a_bnd01_idx_unsigned": [("1 0", P, [], "single element"), ("0 0", T, [], "empty array")],
    "a_bnd02_idx_signed": [("4 2147483647", T, [], "INT_MAX index"), ("0 0", T, [], "empty array")],
    "a_bnd04_memcpy_range": [("16 16 0", P, [], "off == cap, len 0"), ("16 0 17", T, [], "len == cap + 1"),
                             ("0 0 0", P, [], "zero capacity")],
    "a_bnd05_loop_copy": [("8 8", P, [], "n == Alive2 unroll bound"), ("8 9", T, [], "trip one past unroll bound"),
                          ("12 12", P, [], "beyond unroll bound: differential only"), ("0 0", P, [], "empty")],
    "a_bnd08_matrix": [("3 4 2 4", T, [], "c == cols"), ("3 4 2 3", P, [], "last cell")],
    "a_ovf01_uadd_wrap": [("0 0", P, [], ""), ("4294967295 0", P, [], "UINT_MAX + 0"),
                          ("1 4294967295", T, [], "operands swapped")],
    "a_ovf02_sadd_precheck": [("-2147483647 -1", P, [], "sum == INT_MIN exactly"), ("0 2147483647", P, [], "sum == INT_MAX"),
                              ("1 2147483647", T, [], "swapped positive overflow"), ("-2147483648 0", P, [], "INT_MIN + 0")],
    "a_ovf04_builtin_add": [("-2147483648 0", P, [], ""), ("2147483647 -2147483648", P, [], "sum == -1")],
    "a_ovf05_len_header": [("0", P, [], "")],
    "a_ovf06_usub_underflow": [("0 0", P, [], ""), ("0xffffffffffffffff 0xffffffffffffffff", P, [], "SIZE_MAX - SIZE_MAX")],
    "a_ovf07_signed_len": [("0", P, [], ""), ("-9223372036854775808", T, [], "LONG_MIN")],
    "a_ovf08_shift_amount": [("0xffffffff 31", P, [], "max shift"), ("1 33", T, [], ""), ("1 4294967295", T, [], "UINT_MAX shift")],
    "b_ptr01_wrap_check": [("0", P, [], "len 0")],
    "b_ptr02_wrap_or_end": [("16 0", P, [], "p == end, len 0 (one-past is legal)"),
                            ("8 0xfffffffffffffff8", T, ["ubsan:pointer-overflow"], "p + len wraps exactly to buf")],
}


def main(seeds_dir):
    for sid, items in NEW.items():
        f = Path(seeds_dir) / sid / "inputs.json"
        d = json.loads(f.read_text())
        have = {" ".join(i["args"]) for i in d["inputs"]}
        for args, g, rep, note in items:
            if args in have:
                continue
            inp = {"args": args.split(" "), "guard": g, "expect_reports": rep, "expect_guard_output": g == T, "boundary": True}
            if note:
                inp["note"] = note
            d["inputs"].append(inp)
        with open(f, "w", newline="\n") as fh:
            fh.write(json.dumps(d, indent=2) + "\n")
    print(f"added boundary inputs to {len(NEW)} seeds")


if __name__ == "__main__":
    main(sys.argv[1])
