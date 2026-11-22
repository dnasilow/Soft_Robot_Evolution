#!/usr/bin/env bash
# Copy the results of re-runs of the original 2013 experiment (run_2013_search.sh) from the WSL
# side to results/rerun2013/<run>/ in the project (results/ is kept out of git):
# the learning curve, the settings file, start/finish times and, if the run has reached it, the
# robots of its last recorded generation as one archive. Safe to run while runs are in progress.
# Usage (from Windows):
#   wsl -d Ubuntu -- bash -c "tr -d '\r' < /mnt/c/SoftRobotEvolution/paper/reference_2013/collect_2013_runs.sh | bash"
set -euo pipefail

RUNS="$HOME/softbots2013_ref/runs"
OUT=/mnt/c/SoftRobotEvolution/results/rerun2013
PREFIX="${PREFIX:-}"

mkdir -p "$OUT"
n=0
for d in "$RUNS"/${PREFIX}*/; do
  [ -d "$d" ] || continue
  name=$(basename "$d")
  curve=$(ls "$d"/*Genchamp-AvgFit.txt 2>/dev/null | head -1 || true)
  [ -n "$curve" ] || continue
  mkdir -p "$OUT/$name"
  cp "$curve" "$OUT/$name/curve.txt"
  cp "$d/softbotTest.dat" "$OUT/$name/" 2>/dev/null || true
  for f in started finished failed; do [ -e "$d/$f" ] && cp "$d/$f" "$OUT/$name/" || true; done
  last=$(ls -d "$d"/Gen_* 2>/dev/null | sort | tail -1 || true)
  if [ -n "$last" ]; then
    tar -czf "$OUT/$name/$(basename "$last").tgz" -C "$d" "$(basename "$last")"
  fi
  gens=$(grep -vc '^#' "$curve" || true)
  echo "$name: $gens generations$([ -e "$d/finished" ] && echo ', finished' || echo ', running')$([ -e "$d/failed" ] && echo ', FAILED' || true)"
  n=$((n + 1))
done
echo "$n runs collected into $OUT"
