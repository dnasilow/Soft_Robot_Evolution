#!/usr/bin/env bash
# Copy the results of re-runs of the original 2013 experiment (run_2013_search.sh) from the WSL
# side to results/rerun2013/<run>/ in the project (results/ is kept out of git), and report where
# each run is. Safe to run while runs are in progress.
#   every time:           the learning curve, the settings file, start and finish times
#   once a run finished:  the robots of its last generation (Gen_XXXX.tgz) and of every recorded
#                         generation (all_generations.tgz; the settings record every tenth), the
#                         genomes of the final population and of the champions as the program
#                         saved them, and its log
# Usage (from Windows):
#   wsl -d Ubuntu -- bash -c "tr -d '\r' < /mnt/c/SoftRobotEvolution/paper/reference_2013/collect_2013_runs.sh | bash"
#   PREFIX      only run folders whose name starts with this (default: all)
#   SNAPSHOT=1  also archive the newest generation folder of runs that have not finished
# One line per run:
#   <name>: <n> generations, finished | running | interrupted | FAILED (exit <code>)
# "interrupted" is a run that neither finished nor has a process any more.
set -euo pipefail

RUNS="$HOME/softbots2013_ref/runs"
OUT=/mnt/c/SoftRobotEvolution/results/rerun2013
PREFIX="${PREFIX:-}"
SNAPSHOT="${SNAPSHOT:-0}"

mkdir -p "$OUT"
alive=$(for pid in $(pgrep -x Hypercube_NEAT || true); do readlink "/proc/$pid/cwd" 2>/dev/null || true; done)
n=0
for d in "$RUNS"/${PREFIX}*/; do
  [ -d "$d" ] || continue
  d="${d%/}"
  name=$(basename "$d")
  case "$name" in _*) continue ;; esac
  mkdir -p "$OUT/$name"
  gens=0
  curve=$(ls "$d"/*Genchamp-AvgFit.txt 2>/dev/null | head -1 || true)
  if [ -n "$curve" ]; then
    cp "$curve" "$OUT/$name/curve.txt"
    gens=$(grep -c '^[0-9]' "$curve" || true)
  fi
  cp "$d/softbotTest.dat" "$OUT/$name/" 2>/dev/null || true
  for f in started finished failed; do
    if [ -e "$d/$f" ]; then cp "$d/$f" "$OUT/$name/"; fi
  done

  if [ -e "$d/failed" ]; then state="FAILED ($(cat "$d/failed"))"
  elif [ -e "$d/finished" ]; then state=finished
  elif grep -qxF "$d" <<< "$alive"; then state=running
  else state=interrupted
  fi

  last=$(ls -d "$d"/Gen_* 2>/dev/null | sort | tail -1 || true)
  if [ "$state" = finished ] && [ ! -e "$OUT/$name/collected" ]; then
    if [ -n "$last" ]; then
      tar -czf "$OUT/$name/$(basename "$last").tgz" -C "$d" "$(basename "$last")"
      # The settings record the whole population every RecordEntireGenEvery (10) generations.
      ( cd "$d" && tar -czf "$OUT/$name/all_generations.tgz" Gen_* )
    fi
    for f in "$d"/*_best.xml.gz; do
      if [ -e "$f" ]; then cp "$f" "$OUT/$name/champion_genomes.xml.gz"; fi
    done
    if [ -e "$d/${name}_pop.xml" ]; then gzip -c "$d/${name}_pop.xml" > "$OUT/$name/final_population.xml.gz"; fi
    if [ -e "$d/log.txt" ]; then gzip -c "$d/log.txt" > "$OUT/$name/log.txt.gz"; fi
    if [ -s "$d/err.txt" ]; then cp "$d/err.txt" "$OUT/$name/err.txt"; fi
    touch "$OUT/$name/collected"
  elif [ "$state" != finished ] && [ "$SNAPSHOT" = 1 ] && [ -n "$last" ]; then
    tar -czf "$OUT/$name/$(basename "$last").tgz" -C "$d" "$(basename "$last")"
  fi

  echo "$name: $gens generations, $state"
  n=$((n + 1))
done
echo "$n runs collected into $OUT"
