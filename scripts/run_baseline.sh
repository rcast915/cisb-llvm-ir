#!/usr/bin/env bash
# M3: baseline pipelines over all seeds -> results/baseline.csv
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/env.sh
exec python3 -I driver/run_baseline.py "$@"
