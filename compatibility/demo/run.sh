#!/usr/bin/env bash
set -eo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
mkdir -p "$DEMO_ROOT/logs" "$RESULTS_DIR"
variants=(0_naive 1_preload_gamma 2_multi_core 3_vf 4_double_buffer 5_ub_utilization 6_binary_sum)
# With no arguments, run the complete source progression.
(( $# )) || set -- 0 1 2 3 4 5 6
total=$#
current=0
for stage in "$@"; do
    [[ $stage =~ ^[0-6]$ ]] || { echo "Invalid stage: $stage" >&2; exit 2; }
    name="rms_norm_quant_${variants[$stage]}"
    exe="$BUILD_DIR/Samples/2_Performance/rms_norm_quant_story/$name"
    [[ -x "$exe" ]] || { echo "Build first: $exe" >&2; exit 1; }
    log="$DEMO_ROOT/logs/${name}_$(date +%Y%m%d_%H%M%S).log"
    current=$((current + 1))
    timeout=900
    [[ $stage == 0 || $stage == 1 ]] && timeout=3600
    timeout=${DEMO_TIMEOUT_SECONDS:-$timeout}
    printf "[%d/%d] %s — running; log: %s\n" "$current" "$total" "$name" "$log"
    if ! (
        set -x
        DEMO_TIMEOUT_SECONDS="$timeout" python3 "$DEMO_ROOT/demo/limited_run.py" python3 -m npusim.main record "$exe" -s Ascend950 -g vf -n "${REPORT_CORES:-0}" -o "$RESULTS_DIR/$name"
    ) > "$log" 2>&1; then
        echo "FAILED: $name. Full log: $log" >&2
        tail -n 40 "$log" >&2
        exit 1
    fi
    # Samples return zero even on precision mismatches, so check their output.
    if ! python3 -c 'import pathlib, sys; sys.exit("Compare Difference length 0" not in pathlib.Path(sys.argv[1]).read_text())' "$log"; then
        echo "No successful numerical comparison in $log" >&2
        exit 1
    fi
    # Require artifacts from this run, rather than accepting an older profile.
    python3 - "$log" "$RESULTS_DIR/$name" "$name" <<'CHECK'
import json, pathlib, re, sys
text = pathlib.Path(sys.argv[1]).read_text(errors='replace')
runs = re.findall(r'npusim_\d{14}_' + re.escape(sys.argv[3]), text)
if not runs:
    raise SystemExit('No recorded profile path in ' + sys.argv[1])
run = pathlib.Path(sys.argv[2]) / runs[-1]
summaries = list(run.glob('report/**/summary.json'))
if not summaries or not list(run.glob('report/**/*vf_report.json')):
    raise SystemExit('Incomplete summary/VF report: ' + str(run))
for path in summaries:
    json.loads(path.read_text())
CHECK
    printf "[%d/%d] %s — OK (precision passed, reports saved)\n" "$current" "$total" "$name"
done

# Refresh the artifact index after a successful sequence.
python3 "$DEMO_ROOT/demo/summarize.py" > "$DEMO_ROOT/logs/summary.log"
printf "Done. Open %s/README.md for results.\n" "$DEMO_ROOT"
