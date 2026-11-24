#!/usr/bin/env bash
# Build a SECOND copy of the original 2013 simulator that can also record the motion of a robot,
# for videos. It is the same source as build_2013_simulator.sh builds, with the same compiler
# flags, plus the patch in patches_2013_trace/: four marked additions to main.cpp that write the
# position, rotation and size of every voxel to a file at regular times. They only read the
# simulation's state; the result of a simulation is unchanged (checked by
# paper/analysis/render_champions.py on every robot it renders).
#
# It lives in its own folder (~/softbots2013_trace) and under its own name (voxelize_trace). The
# simulator the campaign uses (~/softbots2013_ref/.../voxelize) is not touched, so this can be
# built and used while runs are in progress.
# Usage (from Windows):
#   wsl -d Ubuntu -- bash -c "tr -d '\r' < /mnt/c/SoftRobotEvolution/paper/reference_2013/build_2013_trace.sh | bash"
#
# Recording: VX_TRACE=<file> [VX_TRACE_EVERY=<seconds, default 0.001>] ./voxelize_trace -f robot.vxa
# The file: "voxels N", N lines with the material number of each voxel, then for every recorded
# time one line "t <time> <centre of mass x y z>" and N lines
# "<x y z> <rotation quaternion w x y z> <size x y z>", in metres.
set -euo pipefail

ARCHIVE=/mnt/c/SoftRobotEvolution/research_reference/repositories/softbots2013Code.tgz
PATCHES=/mnt/c/SoftRobotEvolution/paper/reference_2013/patches_2013_trace
T="$HOME/softbots2013_trace"

rm -rf "$T"
mkdir -p "$T"
cd "$T"
tar -xzf "$ARCHIVE" softbots/Voxel_Sim_NoGui
cd softbots/Voxel_Sim_NoGui
rm -f voxelize
find . -name '*.o' -delete
sed -i 's/\r$//' Voxelyze/main.cpp          # the archive's main.cpp has Windows line ends
for p in "$PATCHES"/*.patch; do
  echo "applying $(basename "$p")"
  tr -d '\r' < "$p" | patch -p1 --quiet
done

INC="-I./zlib-1.2.5 -I./Voxelyze -I./TinyXML"
make -f MakefileG++ -j 8 \
  CFLAGS="-O3 -w -std=gnu89 $INC" \
  CPPFLAGS="-O3 -w -std=gnu++98 -fpermissive -include cstring -include cstdlib -include cstdio $INC" \
  > build.log 2>&1 || { echo "BUILD FAILED - last lines of build.log:"; tail -n 40 build.log; exit 1; }
mv voxelize voxelize_trace

echo "build ok: $(pwd)/voxelize_trace"
ls -la voxelize_trace
sha256sum voxelize_trace | cut -c1-16
