"""Run LLVM verification, selected optimizations, differential execution, and Alive2."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Sequence

from .analysis import compare_guard_shapes


def find_tool(explicit: str | None, names: Sequence[str]) -> str | None:
    if explicit:
        resolved = shutil.which(explicit) if os.path.sep not in explicit else explicit
        return str(Path(resolved).resolve()) if resolved and Path(resolved).exists() else None
    for name in names:
        path = shutil.which(name)
        if path:
            return path
    return None


def run_command(command: list[str], timeout: float) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        result = subprocess.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        return {
            "command": command,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timed_out": False,
            "seconds": round(time.perf_counter() - started, 6),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "returncode": None,
            "stdout": exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or ""),
            "stderr": exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or ""),
            "timed_out": True,
            "seconds": round(time.perf_counter() - started, 6),
        }
    except OSError as exc:
        return {
            "command": command,
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
            "timed_out": False,
            "seconds": round(time.perf_counter() - started, 6),
        }


def sanitizer_hit(run: dict[str, Any]) -> bool:
    output = (run.get("stdout", "") + "\n" + run.get("stderr", "")).lower()
    patterns = (
        "addresssanitizer",
        "undefinedbehaviorsanitizer",
        "runtime error:",
        "ubsan:",
        "sanitizer: deadlysignal",
    )
    return any(pattern in output for pattern in patterns)


def executions_differ(left: dict[str, Any], right: dict[str, Any]) -> bool:
    # stderr is intentionally excluded: paths and sanitizer diagnostics can differ.
    return left.get("returncode") != right.get("returncode") or left.get("stdout") != right.get("stdout")


def version(tool: str, timeout: float = 5.0) -> str:
    result = run_command([tool, "--version"], timeout)
    first = (result.get("stdout") or result.get("stderr") or "").splitlines()
    return first[0] if first else "version unavailable"


def classify_alive2(output: str, returncode: int | None) -> str:
    lowered = output.lower()
    if "transformation seems to be correct" in lowered:
        return "proven_correct"
    if any(marker in lowered for marker in (
        "(unsound)", "counterexample", "transformation doesn't verify",
        "transformation does not verify", "not equivalent", "mismatch in", "unsound transformation",
    )):
        return "counterexample_or_unsound"
    if "timeout" in lowered or "timed out" in lowered:
        return "timeout"
    if returncode not in (0, None):
        return "tool_error_or_inconclusive"
    return "inconclusive_check_output"


def short_run(run: dict[str, Any] | None) -> dict[str, Any] | None:
    if run is None:
        return None
    return {
        "command": run.get("command"),
        "returncode": run.get("returncode"),
        "timed_out": run.get("timed_out", False),
        "seconds": run.get("seconds"),
        "sanitizer_report": sanitizer_hit(run),
        "stdout": run.get("stdout", "")[-2000:],
        "stderr": run.get("stderr", "")[-3000:],
    }


def process_case(
    case: Path,
    out_root: Path,
    opt: str,
    clang: str,
    alive_tv: str | None,
    passes: str,
    sanitizers: str,
    timeout: float,
) -> dict[str, Any]:
    case_out = out_root / case.stem
    case_out.mkdir(parents=True, exist_ok=True)
    optimized = case_out / "optimized.ll"
    original_exe = case_out / "original.bin"
    optimized_exe = case_out / "optimized.bin"
    original_bytes = case.read_bytes()
    original_text = original_bytes.decode("utf-8", errors="replace")
    record: dict[str, Any] = {
        "case": str(case),
        "source_sha256": hashlib.sha256(original_bytes).hexdigest(),
        "passes": passes,
        "sanitizers": sanitizers,
        "status": "started",
        "original_ir": str(case),
        "optimized_ir": str(optimized),
    }

    verify = run_command([opt, "-passes=verify", "-disable-output", str(case)], timeout)
    record["input_verification"] = short_run(verify)
    if verify["returncode"] != 0 or verify["timed_out"]:
        record["status"] = "invalid_input_ir_or_verifier_error"
        record["verifier_stderr"] = verify["stderr"][-4000:]
        return record

    optimize = run_command(
        [opt, "-S", "-verify-each", f"-passes={passes}", str(case), "-o", str(optimized)],
        timeout,
    )
    record["optimization"] = short_run(optimize)
    if optimize["returncode"] != 0 or optimize["timed_out"] or not optimized.exists():
        record["status"] = "optimizer_error_or_timeout"
        record["optimizer_stderr"] = optimize["stderr"][-4000:]
        return record

    optimized_bytes = optimized.read_bytes()
    optimized_text = optimized_bytes.decode("utf-8", errors="replace")
    record["optimized_sha256"] = hashlib.sha256(optimized_bytes).hexdigest()
    guard_audit = compare_guard_shapes(original_text, optimized_text)
    record["guard_shape_audit"] = guard_audit

    compile_flags: list[str] = []
    if sanitizers != "none":
        compile_flags.append(f"-fsanitize={sanitizers}")
        compile_flags.append("-fno-omit-frame-pointer")
    base_flags = [clang, "-Wno-override-module", "-O0", "-x", "ir"]
    comp_original = run_command(base_flags + [str(case), "-o", str(original_exe)] + compile_flags, timeout)
    comp_optimized = run_command(base_flags + [str(optimized), "-o", str(optimized_exe)] + compile_flags, timeout)
    record["compile_original"] = short_run(comp_original)
    record["compile_optimized"] = short_run(comp_optimized)

    execution_original: dict[str, Any] | None = None
    execution_optimized: dict[str, Any] | None = None
    if comp_original["returncode"] == 0 and comp_optimized["returncode"] == 0:
        execution_original = run_command([str(original_exe)], timeout)
        execution_optimized = run_command([str(optimized_exe)], timeout)
        record["execution_original"] = short_run(execution_original)
        record["execution_optimized"] = short_run(execution_optimized)
        record["runtime_divergence"] = executions_differ(execution_original, execution_optimized)
        original_san = sanitizer_hit(execution_original)
        optimized_san = sanitizer_hit(execution_optimized)
        record["optimized_only_sanitizer_report"] = optimized_san and not original_san
    else:
        record["runtime_divergence"] = None
        record["optimized_only_sanitizer_report"] = False

    if alive_tv:
        alive = run_command([alive_tv, str(case), str(optimized)], timeout)
        alive_output = (alive.get("stdout", "") + "\n" + alive.get("stderr", "")).strip()
        (case_out / "alive2.log").write_text(alive_output + "\n", encoding="utf-8")
        record["alive2"] = {
            "status": classify_alive2(alive_output, alive["returncode"]),
            "returncode": alive["returncode"],
            "timed_out": alive["timed_out"],
            "seconds": alive["seconds"],
            "log": str(case_out / "alive2.log"),
            "output_tail": alive_output[-3000:],
        }
    else:
        record["alive2"] = {"status": "not_installed_or_not_configured"}

    if comp_original["returncode"] != 0 or comp_optimized["returncode"] != 0 or comp_original["timed_out"] or comp_optimized["timed_out"]:
        record["status"] = "compile_error_or_timeout"
    elif record.get("optimized_only_sanitizer_report"):
        record["status"] = "high_priority_candidate_optimized_only_sanitizer_report"
    elif record.get("runtime_divergence"):
        record["status"] = "candidate_runtime_divergence"
    elif record["guard_shape_audit"]["review_recommended"]:
        record["status"] = "review_guard_shape_change"
    elif record["alive2"].get("status") == "counterexample_or_unsound":
        record["status"] = "review_alive2_counterexample"
    else:
        record["status"] = "no_signal_in_this_run"
    return record


def write_summary(out_root: Path, records: list[dict[str, Any]], passes: str, sanitizers: str) -> None:
    payload = {
        "schema_version": 1,
        "passes": passes,
        "sanitizers": sanitizers,
        "case_count": len(records),
        "status_counts": {},
        "cases": records,
        "limitations": [
            "IR-shape reductions are heuristic review signals, not proof of a vulnerability.",
            "Dynamic tests only exercise the specific main() inputs present in each .ll file.",
            "Alive2 results depend on its supported LLVM semantics, limits, version compatibility, and configured timeout.",
            "A clean run is not proof of memory safety or compiler correctness.",
        ],
    }
    for record in records:
        status = record.get("status", "unknown")
        payload["status_counts"][status] = payload["status_counts"].get(status, 0) + 1
    (out_root / "summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# CISB IR test run", "", f"- Pass pipeline: `{passes}`", f"- Sanitizers: `{sanitizers}`",
        f"- Cases: {len(records)}", "", "## Summary", "", "| Case | Status | Runtime divergence | Guard-shape review | Alive2 |",
        "|---|---|---:|---:|---|",
    ]
    for record in records:
        case_name = Path(record.get("case", "unknown")).name
        guard_change = bool(record.get("guard_shape_audit", {}).get("review_recommended", False))
        lines.append(
            f"| `{case_name}` | {record.get('status', 'unknown')} | "
            f"{record.get('runtime_divergence', 'n/a')} | {guard_change} | "
            f"{record.get('alive2', {}).get('status', 'n/a')} |"
        )
    lines += [
        "", "## Interpretation", "",
        "Treat every signal as a triage lead. Minimize the IR, verify the reproducer, inspect the pass-by-pass diff, "
        "and use Alive2 where supported before describing a result as a compiler bug. No signal in this run is not proof of correctness.",
    ]
    (out_root / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=Path("cases"), help="Directory containing .ll test cases (searched recursively)")
    parser.add_argument("--out", type=Path, default=Path("artifacts/run"), help="Output directory")
    parser.add_argument("--passes", default="instcombine,simplifycfg,gvn", help="LLVM new-pass-manager pipeline")
    parser.add_argument("--sanitizers", default="none", help="none, address, undefined, or address,undefined")
    parser.add_argument("--opt", help="Path or command name for opt")
    parser.add_argument("--clang", help="Path or command name for clang")
    parser.add_argument("--alive-tv", help="Optional path or command name for Alive2 alive-tv")
    parser.add_argument("--timeout", type=float, default=5.0, help="Timeout in seconds per external command")
    args = parser.parse_args()

    opt = find_tool(args.opt, [f"opt-{v}" for v in range(30, 13, -1)] + ["opt"])
    clang = find_tool(args.clang, [f"clang-{v}" for v in range(30, 13, -1)] + ["clang"])
    alive_tv = find_tool(args.alive_tv, ["alive-tv"]) if args.alive_tv else find_tool(None, ["alive-tv"])
    if not opt:
        print("ERROR: LLVM opt was not found. Install LLVM or pass --opt /path/to/opt.", file=sys.stderr)
        return 2
    if not clang:
        print("ERROR: clang was not found. Install Clang or pass --clang /path/to/clang.", file=sys.stderr)
        return 2
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if args.sanitizers not in {"none", "address", "undefined", "address,undefined"}:
        parser.error("--sanitizers must be none, address, undefined, or address,undefined")
    if not args.cases.is_dir():
        parser.error(f"Cases directory not found: {args.cases}")
    cases = sorted(args.cases.rglob("*.ll"))
    if not cases:
        parser.error(f"No .ll test cases found under {args.cases}")

    args.out.mkdir(parents=True, exist_ok=True)
    tool_info = {
        "opt": {"path": opt, "version": version(opt)},
        "clang": {"path": clang, "version": version(clang)},
        "alive_tv": {"path": alive_tv, "version": version(alive_tv) if alive_tv else None},
    }
    (args.out / "tools.json").write_text(json.dumps(tool_info, indent=2), encoding="utf-8")
    records = []
    for case in cases:
        print(f"[cisb] {case}", flush=True)
        try:
            record = process_case(case, args.out, opt, clang, alive_tv, args.passes, args.sanitizers, args.timeout)
        except Exception as exc:  # Keep a single malformed case from stopping the corpus.
            record = {"case": str(case), "passes": args.passes, "status": "harness_exception", "error": repr(exc)}
        records.append(record)
        print(f"       -> {record.get('status')}", flush=True)
    write_summary(args.out, records, args.passes, args.sanitizers)
    print(f"Wrote {args.out / 'summary.md'} and {args.out / 'summary.json'}")
    if not alive_tv:
        print("NOTE: alive-tv not found; translation validation was skipped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
