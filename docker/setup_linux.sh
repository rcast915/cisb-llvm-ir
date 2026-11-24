#!/usr/bin/env bash
# Linux equivalent of scripts/setup.sh: record versions, run M1 self-tests.
set -euo pipefail
cd /workspace
source scripts/env.sh
mkdir -p results
{
  echo "date: $(date -u +%FT%TZ)"
  echo "host: $(uname -sm) $(. /etc/os-release; echo "$PRETTY_NAME") (Docker on Windows 11)"
  echo "clang: $(realpath "$CLANG") | $("$CLANG" --version | head -1)"
  echo "opt: $(realpath "$OPT") | $("$OPT" --version | grep -m1 version | xargs)"
  echo "alive-tv: $ALIVE_TV | built from: $(tr '\n' ';' < /opt/alive2/BUILD_REF.txt)"
  echo "z3: $(z3 --version)"
  echo "python: $(python3 --version)"
  echo "triple: $("$CLANG" -print-target-triple)"
} | tee results/versions.txt
bash validate/m1/run_m1.sh
bash validate/m1/run_sanitizers.sh
