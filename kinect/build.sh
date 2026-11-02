#!/usr/bin/env bash
# Builds the Kinect v2 helper (kinect/bin/cellokinect) and the library it
# needs, libfreenect2 (OpenKinect, not in Homebrew), into kinect/.
# Needs Homebrew; installs libusb, jpeg-turbo, glfw, cmake and pkg-config.
#   bash kinect/build.sh            # skips what is already built
#   bash kinect/build.sh --force    # rebuild everything
set -euo pipefail
cd "$(dirname "$0")"
HERE="$(pwd)"
# the commit this was tested with (libfreenect2 has not changed since 2020)
REV=fd64c5d9b214df6f6a55b4419357e51083f15d93
FORCE=0
[ "${1:-}" = "--force" ] && FORCE=1

say() { printf '\033[1;33m==>\033[0m %s\n' "$*"; }

if [ $FORCE = 1 ]; then rm -rf libfreenect2/build prefix bin; fi

if [ ! -f prefix/lib/libfreenect2.dylib ]; then
    command -v brew >/dev/null || { echo "Homebrew is needed: https://brew.sh"; exit 1; }
    say "Homebrew packages for libfreenect2"
    brew list libusb jpeg-turbo glfw cmake pkg-config >/dev/null 2>&1 ||
        brew install libusb jpeg-turbo glfw cmake pkg-config
    if [ ! -d libfreenect2/.git ]; then
        say "Downloading libfreenect2"
        git clone https://github.com/OpenKinect/libfreenect2.git
    fi
    git -C libfreenect2 fetch --depth 1 origin "$REV" 2>/dev/null || true
    git -C libfreenect2 checkout -q "$REV"
    say "Building libfreenect2"
    mkdir -p libfreenect2/build
    # CMAKE_POLICY_VERSION_MINIMUM: its CMakeLists predates CMake 4
    cmake -S libfreenect2 -B libfreenect2/build -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_INSTALL_PREFIX="$HERE/prefix" \
        -DENABLE_CUDA=OFF -DENABLE_OPENCL=OFF -DENABLE_OPENGL=ON -DBUILD_EXAMPLES=OFF \
        > build.log 2>&1 || { tail -30 build.log; exit 1; }
    cmake --build libfreenect2/build -j "$(sysctl -n hw.ncpu)" --target install \
        >> build.log 2>&1 || { tail -30 build.log; exit 1; }
fi

if [ ! -x bin/cellokinect ] || [ cellokinect.cpp -nt bin/cellokinect ]; then
    say "Building the Kinect helper"
    mkdir -p bin
    clang++ -std=c++14 -O2 -o bin/cellokinect cellokinect.cpp \
        -I prefix/include -L prefix/lib -lfreenect2 -Wl,-rpath,"@executable_path/../prefix/lib"
fi
say "Kinect helper ready: kinect/bin/cellokinect"
