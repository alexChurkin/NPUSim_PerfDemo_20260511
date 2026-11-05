#!/usr/bin/env bash
# Source this file from bash. Override paths before sourcing when moving the demo.
DEMO_ROOT="${DEMO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SAMPLES_DIR="${SAMPLES_DIR:-$DEMO_ROOT/cann-samples}"
source "$DEMO_ROOT/demo/python.sh"
SIMULATOR_DIR="${SIMULATOR_DIR:-$DEMO_ROOT/npu-simulator}"
BUILD_DIR="${BUILD_DIR:-$DEMO_ROOT/build}"
RESULTS_DIR="${RESULTS_DIR:-$DEMO_ROOT/results}"
if [[ -z ${CANN_SETENV:-} ]]; then
    CANN_SETENV=$(python3 "$DEMO_ROOT/demo/select_cann.py") || return 1
fi
[[ -f "$CANN_SETENV" ]] || { echo "Missing CANN environment: $CANN_SETENV" >&2; return 1; }
[[ -f "$SIMULATOR_DIR/npusim/main.py" ]] || { echo "Missing simulator sources: $SIMULATOR_DIR" >&2; return 1; }
printf 'CANN: %s\n' "$CANN_SETENV"
# Vendor initialization expects unset variables to be allowed.
_demo_nounset=0
[[ $- == *u* ]] && _demo_nounset=1
set +u
source "$CANN_SETENV" . || { (( _demo_nounset )) && set -u; return 1; }
(( _demo_nounset )) && set -u
unset _demo_nounset
export DEMO_ROOT SAMPLES_DIR SIMULATOR_DIR BUILD_DIR RESULTS_DIR CANN_SETENV
# Force imports from the requested checkout, including prof_demo.
export PYTHONPATH="$SIMULATOR_DIR${PYTHONPATH:+:$PYTHONPATH}"
# Bootstrap installs numpy here without touching system Python.
PYTHON_DEPS="$DEMO_ROOT/python-deps/$(python3 -c 'import sys; print("cp%d%d" % sys.version_info[:2])')"
export PYTHON_DEPS
if [[ -d "$PYTHON_DEPS" ]]; then
    export PYTHONPATH="$PYTHON_DEPS:$PYTHONPATH"
fi
export CANNSIM_COLLECT=all
export BIPROF_OPTS='-l debug --save_tmp_files --scalar-ipc --vec-ipc --simd-perf --memory-utilization -j 1'

# Keep the runtime scope-filter build inside the portable workspace.
if [[ -z ${NPUSIM_SCOPE_FILTER_LIB:-} ]]; then
    mkdir -p "$DEMO_ROOT/.cache"
    _demo_filter="$DEMO_ROOT/.cache/libdlopen_scope_filter.so"
    _demo_filter_src="$SIMULATOR_DIR/npusim/core/record/dlopen_scope_filter.c"
    if [[ ! -f "$_demo_filter" || "$_demo_filter_src" -nt "$_demo_filter" ]]; then
        cc -shared -fPIC -O2 -o "$_demo_filter" "$_demo_filter_src" || return 1
    fi
    export NPUSIM_SCOPE_FILTER_LIB="$_demo_filter"
    unset _demo_filter _demo_filter_src
fi

# Limit model worker threads without modifying the installed CANN files.
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
if [[ -z ${CAMODEL_CONFIG_PATH:-} ]]; then
    mkdir -p "$DEMO_ROOT/.cache"
    printf '{"sysconf":{"esl_top_thread_cnt":2}}\n' > "$DEMO_ROOT/.cache/camodel-limited.json"
    export CAMODEL_CONFIG_PATH="$DEMO_ROOT/.cache/camodel-limited.json"
fi
