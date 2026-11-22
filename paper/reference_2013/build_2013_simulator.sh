#!/usr/bin/env bash
# Build the original 2013 headless simulator (Voxel_Sim_NoGui) from the authors' source archive,
# unmodified, inside WSL Ubuntu.  Usage (from Windows):
#   wsl -d Ubuntu -- bash -c "tr -d '\r' < /mnt/c/SoftRobotEvolution/paper/reference_2013/build_2013_simulator.sh | bash"
#
# Notes
#  - The archive's default Makefile targets the Intel compiler (icpc -xhost -O3), which is what the
#    2013 runs used. We build with g++ through the archive's own MakefileG++ (g++ -O3).
#  - The only changes are compiler FLAGS, needed because the code is from 2012-13:
#      C  : -std=gnu89      (zlib 1.2.5 uses old-style function definitions)
#      C++: -std=gnu++98 -fpermissive, and <cstring>/<cstdlib>/<cstdio> force-included
#    No source file is edited.
#  - The prebuilt 'voxelize' binary shipped in the archive is deleted, not run.
set -euo pipefail

ARCHIVE=/mnt/c/SoftRobotEvolution/research_reference/repositories/softbots2013Code.tgz
REF="$HOME/softbots2013_ref"

rm -rf "$REF"
mkdir -p "$REF"
cd "$REF"
tar -xzf "$ARCHIVE" softbots/Voxel_Sim_NoGui
cd softbots/Voxel_Sim_NoGui
rm -f voxelize
find . -name '*.o' -delete

INC="-I./zlib-1.2.5 -I./Voxelyze -I./TinyXML"
make -f MakefileG++ -j 16 \
  CFLAGS="-O3 -w -std=gnu89 $INC" \
  CPPFLAGS="-O3 -w -std=gnu++98 -fpermissive -include cstring -include cstdlib -include cstdio $INC" \
  > build.log 2>&1 || { echo "BUILD FAILED - last lines of build.log:"; tail -n 40 build.log; exit 1; }

echo "build ok: $(pwd)/voxelize"
ls -la voxelize
g++ --version | head -1
sha256sum voxelize | cut -c1-16
