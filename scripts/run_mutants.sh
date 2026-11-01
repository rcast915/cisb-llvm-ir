#!/usr/bin/env bash
# M4: generate, filter and evaluate mutants -> results/mutants.csv, results/mutant_runs.csv
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/env.sh
exec python3 -I driver/run_mutants.py "$@"
