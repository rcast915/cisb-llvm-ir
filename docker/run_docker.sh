#!/usr/bin/env bash
# Run the cisb-llvm-ir pipeline (M1 self-tests, M2 seed check, M3 baseline, M4 mutants) in Docker.
# Usage: run_docker.sh <path to an LF-line-ending cisb-llvm-ir checkout> [stage ...]
#   stages: setup seeds baseline mutants all (default: all)
# The repo's scripts/env.sh (macOS/Homebrew paths) is shadowed by env.linux.sh via a bind mount,
# so no repository file is modified.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
repo="$(cd "$1" && pwd)"; shift
stages=("${@:-all}")
img=${CISB_IMAGE:-cisb-linux-z3}
docker image inspect "$img" >/dev/null 2>&1 || { docker build -t cisb-linux "$here" && docker build -f "$here/Dockerfile.z3" -t cisb-linux-z3 "$here"; }

# Git Bash on Windows rewrites /paths in arguments; disable that for docker.
export MSYS_NO_PATHCONV=1
dock() {
  docker run --rm -v "$(cygpath -w "$repo" 2>/dev/null || echo "$repo"):/workspace" \
    -v "$(cygpath -w "$here/env.linux.sh" 2>/dev/null || echo "$here/env.linux.sh"):/workspace/scripts/env.sh:ro" \
    -v "$(cygpath -w "$here/setup_linux.sh" 2>/dev/null || echo "$here/setup_linux.sh"):/opt/setup_linux.sh:ro" \
    -w /workspace "$img" bash -c "$1"
}
for s in "${stages[@]}"; do
  case "$s" in
    setup)    dock "bash /opt/setup_linux.sh 2>&1 | tee results/m1_log.txt" ;;
    seeds)    dock "source scripts/env.sh && python3 -I driver/check_seeds.py 2>&1 | tee results/m2_log.txt" ;;
    baseline) dock "source scripts/env.sh && python3 -I driver/run_baseline.py 2>&1 | tee results/m3_log.txt && python3 -I driver/summarize_baseline.py" ;;
    mutants)  dock "source scripts/env.sh && python3 -I driver/run_mutants.py 2>&1 | tee results/m4_log.txt && python3 -I driver/summarize_mutants.py" ;;
    shell)    docker run --rm -it -v "$(cygpath -w "$repo"):/workspace" -v "$(cygpath -w "$here/env.linux.sh"):/workspace/scripts/env.sh:ro" -w /workspace "$img" bash ;;
    all)      "$0" "$repo" setup seeds baseline mutants ;;
    *) echo "unknown stage $s"; exit 2 ;;
  esac
done
