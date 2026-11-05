#!/usr/bin/env bash
set -eo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
mkdir -p "$DEMO_ROOT/logs"
# CMake caches pin compiler/toolkit paths. Preserve the previous build when
# moving the package or switching CANN, then configure from scratch.
if [[ -f "$BUILD_DIR/CMakeCache.txt" ]]; then
    if ! python3 "$DEMO_ROOT/demo/check_build_path.py" "$BUILD_DIR" "$DEMO_ROOT/demo";
    then
        mv "$BUILD_DIR" "${BUILD_DIR}.previous.$(date +%Y%m%d_%H%M%S).$$"
    fi
fi
{
    set -x
    cmake -S "$DEMO_ROOT/demo" -B "$BUILD_DIR" -DSAMPLES_DIR="$SAMPLES_DIR" -DNPU_ARCH=dav-3510 \
        -DRMS_DEMO_A="${RMS_DEMO_A:-128}" -DRMS_DEMO_R="${RMS_DEMO_R:-256}" -DRMS_DEMO_CORES="${RMS_DEMO_CORES:-32}" -DRMS_DEMO_DEBUG=ON
    cmake --build "$BUILD_DIR" --target "${BUILD_TARGET:-rms_norm_quant_story}" -j "${JOBS:-2}"
} 2>&1 | tee "$DEMO_ROOT/logs/build.log"
