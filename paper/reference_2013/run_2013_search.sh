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
  if [ -e "$d" ]; then echo "$name: folder exists, not overwriting"; return 0; fi
  mkdir -p "$d"
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

mkdir -p "$RUNS"
echo "launching seeds [$SEEDS], $JOBS at a time, generations ${GENS:-as in the settings file}, penalty $PENALTY"
echo $SEEDS | tr ' ' '\n' | xargs -P "$JOBS" -I{} bash -c 'one "$1"' _ {}
echo "all done"
