#!/usr/bin/env bash
# Stop the re-runs whose run folder starts with PREFIX, together with the launch they belong to.
# A launch (run_2013_search.sh) is one process group inside WSL: its bash, xargs, the per-run
# wrappers, the search programs and the simulators. The whole group is ended, so no seed that
# was still waiting its turn is started afterwards.
# What the runs had computed is not continued later: a stopped seed is started again from the
# beginning by run_2013_search.sh with RESTART_INCOMPLETE=1. Finished runs are not affected.
# Usage (from Windows; start_arm.py --stop does this):
#   wsl -d Ubuntu -- bash -c "export PREFIX=armR_P0_s; tr -d '\r' < /mnt/c/SoftRobotEvolution/paper/reference_2013/stop_2013_runs.sh | bash"
set -euo pipefail

RUNS="$HOME/softbots2013_ref/runs"
PREFIX="${PREFIX:?give PREFIX, for example PREFIX=armR_P0_s}"

groups=""
runs=0
for program in Hypercube_NEAT voxelize; do
  for pid in $(pgrep -x "$program" || true); do
    cwd=$(readlink "/proc/$pid/cwd" 2>/dev/null || true)
    case "$cwd" in
      "$RUNS/$PREFIX"*)
        groups="$groups $(ps -o pgid= -p "$pid" 2>/dev/null | tr -d ' ')"
        if [ "$program" = Hypercube_NEAT ]; then runs=$((runs + 1)); fi ;;
    esac
  done
done
launches=0
for g in $(echo $groups | tr ' ' '\n' | sort -u); do
  # never the group of this script, of init, or anything that is not a number above 1
  if [ "$g" -gt 1 ] 2>/dev/null && [ "$g" != "$(ps -o pgid= -p $$ 2>/dev/null | tr -d ' ')" ]; then
    if kill -- "-$g" 2>/dev/null; then launches=$((launches + 1)); fi
  fi
done
sleep 2
left=0
for pid in $(pgrep -x Hypercube_NEAT || true); do
  case "$(readlink "/proc/$pid/cwd" 2>/dev/null || true)" in "$RUNS/$PREFIX"*) left=$((left + 1)) ;; esac
done
echo "$runs runs stopped in $launches launch(es); $left still alive"
