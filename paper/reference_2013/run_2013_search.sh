#!/usr/bin/env bash
# Run the ORIGINAL 2013 experiment: the authors' search program (built by build_2013_search.sh)
# driving the authors' simulator (built by build_2013_simulator.sh), launched the way the 2013
# launch script did it: a run folder holding the two programs and the settings file, then
#     ./Hypercube_NEAT -I <settings> -O <prefix> -R <seed>
# Usage (from Windows), one or several seeds side by side (each run uses one core):
#   wsl -d Ubuntu -- bash -c "export SEEDS='1 2 3' GENS=30 TAG=pilot; tr -d '\r' < /mnt/c/SoftRobotEvolution/paper/reference_2013/run_2013_search.sh | bash"
#
#   SEEDS    random seeds, one run each (default "1")
#   GENS     generations; default: what the settings file says (1000)
#   PENALTY  0 none (default) | 1 voxels | 2 actuated | 3 connections   (the program's -P switch)
#   TAG      name prefix of the run folders (default "rerun")
#   JOBS     how many runs at the same time (default: all of SEEDS)
#   RESTART_INCOMPLETE=1   a run folder that exists but did not finish and is not running is moved
#            to runs/_interrupted/ and that seed is started again from the beginning. The program
#            is deterministic for a given seed, so this repeats the same run. Without it such
#            folders are reported and left alone.
# Finished runs are always skipped, runs in progress are never touched, and a second launch of
# the same TAG and PENALTY while one is in progress is refused (exit code 4).
# For a whole arm of the campaign use start_arm.py, which calls this script.
#
# The settings file is the one deposited with the 2013 data (softbots2013Config). The only edit,
# and only when GENS is given, is its MaxGenerations line in the run folder's own copy.
set -euo pipefail

REF="$HOME/softbots2013_ref"
H="$REF/softbots/hyperneat/HyperNEAT_v2_5"
SIM="$REF/softbots/Voxel_Sim_NoGui/voxelize"
SEARCH="$H/HyperNEAT/out/Hypercube_NEAT"
DAT=/mnt/c/SoftRobotEvolution/research_reference/extracted/dryad/softbots2013Config/config/softbotTest.dat
RUNS="$REF/runs"
SEEDS="${SEEDS:-1}"
GENS="${GENS:-}"
PENALTY="${PENALTY:-0}"
TAG="${TAG:-rerun}"
JOBS="${JOBS:-$(echo $SEEDS | wc -w)}"

for f in "$SIM" "$SEARCH" "$DAT"; do
  [ -e "$f" ] || { echo "missing: $f"; exit 2; }
done
export LD_LIBRARY_PATH="$H/HyperNEAT/out:$H/tinyxmldll/out:$H/zlib/out:${LD_LIBRARY_PATH:-}"

one() {
  seed="$1"
  name="${TAG}_P${PENALTY}_s${seed}"
  d="$RUNS/$name"
  if ! mkdir "$d" 2>/dev/null; then
    # The folder is there already: a finished run, a run in progress, or one that was cut short.
    if [ -e "$d/finished" ] && [ ! -e "$d/failed" ]; then echo "$name: already finished, skipping"; return 0; fi
    for pid in $(pgrep -x Hypercube_NEAT || true); do
      if [ "$(readlink "/proc/$pid/cwd" 2>/dev/null)" = "$d" ]; then echo "$name: is running (pid $pid), skipping"; return 0; fi
    done
    if [ "${RESTART_INCOMPLETE:-0}" != "1" ]; then
      echo "$name: an earlier run of this seed did not finish; left alone (RESTART_INCOMPLETE=1 starts the seed again)"
      return 0
    fi
    mkdir -p "$RUNS/_interrupted"
    mv "$d" "$RUNS/_interrupted/${name}-$(date +%Y%m%d-%H%M%S)"
    echo "$name: unfinished run moved to _interrupted/, starting the seed again"
    mkdir "$d" || { echo "$name: cannot create the run folder"; return 1; }
  fi
  cp "$SIM" "$SEARCH" "$d/"
  tr -d '\r' < "$DAT" > "$d/softbotTest.dat"
  if [ -n "$GENS" ]; then
    sed -i -E "s/^MaxGenerations[[:space:]]+[0-9.]+/MaxGenerations ${GENS}.0/" "$d/softbotTest.dat"
  fi
  cd "$d"
  date +%s > started
  ./Hypercube_NEAT -I softbotTest.dat -O "$name" -R "$seed" -P "$PENALTY" > log.txt 2> err.txt < /dev/null || echo "exit $?" > failed
  date +%s > finished
  echo "$name: done in $(( $(cat finished) - $(cat started) )) s"
}
export -f one
export RUNS SIM SEARCH DAT GENS PENALTY TAG
export RESTART_INCOMPLETE="${RESTART_INCOMPLETE:-0}"

mkdir -p "$RUNS"
# One launch per set of runs at a time. The lock is held by this script only, not by the runs.
exec 9> "$RUNS/.${TAG}_P${PENALTY}.lock"
if ! flock -n 9; then
  echo "another launch of ${TAG}_P${PENALTY} is in progress; nothing started"
  exit 4
fi
echo "launching seeds [$SEEDS], $JOBS at a time, generations ${GENS:-as in the settings file}, penalty $PENALTY"
echo $SEEDS | tr ' ' '\n' | xargs -P "$JOBS" -I{} bash -c 'one "$1"' _ {} 9>&-
echo "all done"
