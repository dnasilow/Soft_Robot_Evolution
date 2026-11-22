#!/usr/bin/env bash
# Replay the deposited generation-1000 robots in the 2013 simulator built by build_2013_simulator.sh
# and record the distance it reports, next to the score recorded in each file name.
# Usage (from Windows):
#   wsl -d Ubuntu -- bash -c "tr -d '\r' < /mnt/c/SoftRobotEvolution/paper/reference_2013/replay_in_2013_simulator.sh | bash"
# Optional: LIMIT=24 to replay only the first 24 files (timing test), JOBS=24 parallel simulations,
#           SRC=<folder of .vxa files laid out as <group>/<run>/Gen_1000/*.vxa>, NAME=<output csv name>.
# Each .vxa is run exactly as deposited: its own physics settings, 0.25 s, its own fitness file name.
set -euo pipefail

REF="$HOME/softbots2013_ref"
SIM="$REF/softbots/Voxel_Sim_NoGui/voxelize"
SRC="${SRC:-/mnt/c/SoftRobotEvolution/research_reference/extracted/dryad_gen1000}"
OUT=/mnt/c/SoftRobotEvolution/paper/reference_2013
NAME="${NAME:-replay_2013_simulator.csv}"
WORK="$REF/work"
LIMIT="${LIMIT:-0}"
JOBS="${JOBS:-24}"

rm -rf "$WORK"
mkdir -p "$WORK"

one() {
  f="$1"
  b=$(basename "$f")
  run=$(basename "$(dirname "$(dirname "$f")")")
  cond=$(basename "$(dirname "$(dirname "$(dirname "$f")")")")
  d=$(mktemp -d -p "$WORK")
  cp "$f" "$d/r.vxa"
  t0=$(date +%s.%N)
  ( cd "$d" && timeout 900 "$SIM" -f r.vxa > /dev/null 2>&1 ) || true
  t1=$(date +%s.%N)
  dist=$(grep -h -o '<FinalCOM_Dist>[^<]*' "$d"/*fitness.xml 2>/dev/null | sed 's/<FinalCOM_Dist>//' | head -1)
  orig=$(echo "$b" | sed -E 's/.*origFit_([0-9.eE+-]+)_genome\.vxa/\1/')
  adj=$(echo "$b" | sed -E 's/.*adjFit_([0-9.eE+-]+)--.*/\1/')
  secs=$(echo "$t1 - $t0" | bc)
  echo "$cond,$run,$b,$orig,$adj,${dist:-NA},$secs"
  rm -rf "$d"
}
export -f one
export SIM WORK

LIST="$WORK/list.txt"
find "$SRC" -name '*.vxa' | sort > "$LIST"
if [ "$LIMIT" != "0" ]; then head -n "$LIMIT" "$LIST" > "$LIST.cut"; mv "$LIST.cut" "$LIST"; fi
N=$(wc -l < "$LIST")
echo "replaying $N robots with $JOBS parallel simulations"
T0=$(date +%s)
TMP="$REF/replay.csv"
echo "condition,run,file,recorded_orig_fit,recorded_adj_fit,final_com_dist_m,seconds" > "$TMP"
xargs -a "$LIST" -P "$JOBS" -d '\n' -I{} bash -c 'one "$1"' _ {} >> "$TMP"
T1=$(date +%s)
echo "done in $((T1 - T0)) s"
if [ "$LIMIT" != "0" ]; then NAME="first${LIMIT}_$NAME"; fi
cp "$TMP" "$OUT/$NAME"
echo "wrote $OUT/$NAME ($(($(wc -l < "$TMP") - 1)) rows, $(grep -c ',NA,' "$TMP" || true) without a result)"
head -n 6 "$TMP"
