#!/usr/bin/env bash
# M2: validate the seed corpus (IR, optnone, guards, sanitizer runs per arm).
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/env.sh
exec python3 -I driver/check_seeds.py "$@"
