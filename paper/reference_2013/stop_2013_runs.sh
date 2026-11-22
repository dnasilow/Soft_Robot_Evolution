#!/usr/bin/env bash
# Stop the re-runs whose run folder starts with PREFIX (search program and simulator processes).
# What they had computed is not continued later: a stopped seed is started again from the
# beginning by run_2013_search.sh with RESTART_INCOMPLETE=1. Finished runs are not affected.
# Usage (from Windows):
#   wsl -d Ubuntu -- bash -c "export PREFIX=armR_P0_s; tr -d '\r' < /mnt/c/SoftRobotEvolution/paper/reference_2013/stop_2013_runs.sh | bash"
set -euo pipefail

RUNS="$HOME/softbots2013_ref/runs"
PREFIX="${PREFIX:?give PREFIX, for example PREFIX=armR_P0_s}"

n=0
for program in Hypercube_NEAT voxelize; do
  for pid in $(pgrep -x "$program" || true); do
    cwd=$(readlink "/proc/$pid/cwd" 2>/dev/null || true)
    case "$cwd" in
      "$RUNS/$PREFIX"*) if kill "$pid" 2>/dev/null; then n=$((n + 1)); fi ;;
    esac
  done
done
echo "$n processes stopped"
