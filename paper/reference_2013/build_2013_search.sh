#!/usr/bin/env bash
# Build the original 2013 search program (HyperNEAT v2.5 with the Softbots experiment) from the
# authors' source archive, inside WSL Ubuntu. It is the program that drove the 2013 runs; it calls
# the simulator built by build_2013_simulator.sh.
# Usage (from Windows):
#   wsl -d Ubuntu -- bash -c "tr -d '\r' < /mnt/c/SoftRobotEvolution/paper/reference_2013/build_2013_search.sh | bash"
#
# Needs (installed once, as root):  apt-get install cmake libboost-dev libboost-filesystem-dev libboost-thread-dev
#
# What is changed, and why
#  - The archive ships the authors' own build caches, generated Makefiles and binaries. They are
#    deleted; nothing prebuilt is used.
#  - Compiler flags only, for the age of the code: C89 for the bundled zlib; for C++,
#    -fpermissive and warnings off. The C++ standard has to be C++14 because the Boost that
#    Ubuntu 26.04 ships (1.90) no longer supports older standards; the 2013 build used Boost 1.51.
#  - CMake is told to accept the old project files (CMAKE_POLICY_VERSION_MINIMUM), and the two
#    bundled-library build files that have no cmake_minimum_required line get one prepended
#    (CMake 4 refuses to configure without it). Build files only; no program source.
#  - compat_2013_search.h is force-included into every C++ file. It resolves names that became
#    ambiguous when the standard library gained its own shared_ptr (see that file).
#  - Any source patch that turns out to be unavoidable is applied from patches_2013_search/ and
#    listed there. Patches must not change behaviour, only let the code compile.
set -euo pipefail

ARCHIVE=/mnt/c/SoftRobotEvolution/research_reference/repositories/softbots2013Code.tgz
PATCHES=/mnt/c/SoftRobotEvolution/paper/reference_2013/patches_2013_search
REF="$HOME/softbots2013_ref"
H="$REF/softbots/hyperneat/HyperNEAT_v2_5"
JOBS="${JOBS:-16}"

mkdir -p "$REF"
cd "$REF"
rm -rf softbots/hyperneat
tar -xzf "$ARCHIVE" softbots/hyperneat
cd "$H"
find . \( -name CMakeCache.txt -o -name cmake_install.cmake \) -delete
find . -name Makefile -not -path './JGTL/*' -delete
find . -name CMakeFiles -type d -prune -exec rm -rf {} +
find . \( -name '*.o' -o -name '*.so' -o -name '*.a' \) -delete
rm -f out/Hypercube_NEAT HyperNEAT/out/Hypercube_NEAT

if [ -d "$PATCHES" ]; then
  for p in "$PATCHES"/*.patch; do
    [ -e "$p" ] || continue
    echo "applying $(basename "$p")"
    tr -d '\r' < "$p" | patch -p1 --quiet
  done
fi

for f in zlib/CMakeLists.txt tinyxmldll/CMakeLists.txt HyperNEAT/CMakeLists.txt; do
  if ! head -n 3 "$f" | grep -qi cmake_minimum_required; then
    sed -i '1i cmake_minimum_required(VERSION 3.5)' "$f"
  fi
done

POL="-DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_BUILD_TYPE=Release"
CF="-w -std=gnu89 -fPIC"
COMPAT=/mnt/c/SoftRobotEvolution/paper/reference_2013/compat_2013_search.h
# BOOST_TIMER_ENABLE_DEPRECATED: the code uses boost/progress.hpp and boost/timer.hpp, which
# current Boost only provides when asked.
# _GLIBCXX_USE_CXX11_ABI=0: the code's own map class (JGTL MapInterface) inserts by memmove on
# arrays of std::pair<std::string, double>. That is only valid for the reference-counted
# std::string of the 2013 standard library; today's std::string points into itself, so a moved
# key is corrupted and settings such as RandomSeed are "not found". This switch selects the old
# string layout, which is what the 2013 build had.
CXXF="-w -std=gnu++14 -fpermissive -fPIC -DBOOST_TIMER_ENABLE_DEPRECATED -D_GLIBCXX_USE_CXX11_ABI=0 -include $COMPAT"
LOG="$H/build.log"
: > "$LOG"
step() {
  local what="$1"; shift
  echo "== $what"
  if ! "$@" >> "$LOG" 2>&1; then
    echo "FAILED at: $what"
    grep -n -E "error|Error" "$LOG" | head -n 40
    exit 1
  fi
}

cd "$H/zlib"
step "zlib: configure" cmake $POL "-DCMAKE_C_FLAGS=$CF" .
step "zlib: make" make -j "$JOBS"
cd "$H/tinyxmldll"
step "tinyxml: configure" cmake $POL "-DCMAKE_CXX_FLAGS=$CXXF" "-DCMAKE_C_FLAGS=$CF" .
step "tinyxml: make" make -j "$JOBS"
cd "$H/HyperNEAT"
step "search program: configure" cmake $POL -DCOMPILE_ODE=OFF "-DJGTL_INCLUDE=$H/JGTL/include" \
  "-DTINYXMLDLL_INCLUDE=$H/tinyxmldll/include" "-DTINYXMLDLL_LIB=$H/tinyxmldll/out" "-DZLIB_INCLUDE=$H/zlib" \
  -DBoost_INCLUDE_DIRS=/usr/include -DBoost_LIBRARY_DIRS=/usr/lib/x86_64-linux-gnu \
  "-DBoost_LIBRARIES=boost_filesystem;boost_thread" "-DCMAKE_CXX_FLAGS=$CXXF" "-DCMAKE_C_FLAGS=$CF" .
step "search program: make" make -j "$JOBS"

echo "build ok"
ls -la "$H/HyperNEAT/out/" | grep -E "Hypercube_NEAT|\.so" || true
g++ --version | head -1
