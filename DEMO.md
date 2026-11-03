# BiProf demo: RmsNormQuant on NPU Simulator

Run these commands in Bash from the directory containing this guide.
All installation and repository paths are configurable.
The examples are `cann-samples/Samples/2_Performance/rms_norm_quant_story/src/0_naive.asc`
through `6_binary_sum.asc`.

## 1. Requirements and transfer

See [DOWNLOAD.md](DOWNLOAD.md) for GitHub LFS downloads, checksum verification,
archive extraction, and offline transfer.

The target needs Linux x86_64, the same CANN 9.3.0 installation with Ascend950/dav-3510
timing simulator support, Python 3.9–3.12 with pip, CMake, make, and a C/C++ compiler
for the runtime helper. Physical NPU hardware is not required.
The simulator Python code and CANN's `libcannsim_helper.so` must have matching versions
and data contracts; this checkout requires `contract_version=7`.

Transfer the entire `NPUSim_Prof_Live_Demo` directory, including both repositories,
`wheelhouse/`, `demo/`, `patches/`, documentation, and recorded results.
Using the distribution archive is the easiest way to do this.
The `build/` directory contains absolute paths and is excluded from the archive.
If a build directory is transferred anyway, the launcher preserves a stale build
as `build.previous.*` and rebuilds at the new location.

Optional explicit path configuration:

```bash
cd /path/to/NPUSim_Prof_Live_Demo
export DEMO_ROOT="$PWD"
export SAMPLES_DIR=/path/to/cann-samples
export SIMULATOR_DIR=/path/to/npu-simulator
export CANN_SETENV=/path/to/cann/bin/setenv.bash
export BUILD_DIR="$DEMO_ROOT/build"
export RESULTS_DIR="$DEMO_ROOT/results"
```

The packaged samples are already modified. If using an original checkout instead,
apply the transfer patch **once**:

```bash
git -C "$SAMPLES_DIR" apply --check "$DEMO_ROOT/patches/rms-small-demo.patch"
git -C "$SAMPLES_DIR" apply "$DEMO_ROOT/patches/rms-small-demo.patch"
```

Do not reapply it to an already modified checkout. For another revision, run
`git apply --check` first and resolve incompatible changes manually.

The launch scripts initialize this environment automatically:

```bash
source "$DEMO_ROOT/demo/env.sh"
# env.sh initializes CANN with:
# source "$CANN_SETENV" .
export CANNSIM_COLLECT=all
export BIPROF_OPTS='-l debug --save_tmp_files --scalar-ipc --vec-ipc --simd-perf --memory-utilization'
python3 -c 'import npusim; print(npusim.__file__)'
python3 -m npusim.main record --help
```

The printed module path must belong to the selected `$SIMULATOR_DIR` checkout.
Installing a simulator wheel is unnecessary: `PYTHONPATH` selects the requested source.
Use `python3 -m npusim.main`; the package has no `npusim.__main__` module.
`start.sh` installs NumPy locally from `wheelhouse/` with `--no-index` when needed.
Wheels for Python 3.9, 3.10, 3.11, and 3.12 on x86_64 are included.
CANN and operating-system tools must already be installed. Tested revisions are in `versions.txt`.

## 2. Build all seven variants

```bash
bash "$DEMO_ROOT/demo/build.sh"
```

Equivalent commands after sourcing `demo/env.sh`:

```bash
cmake -S "$DEMO_ROOT/demo" -B "$BUILD_DIR" -DSAMPLES_DIR="$SAMPLES_DIR" -DNPU_ARCH=dav-3510 \
  -DRMS_DEMO_A=128 -DRMS_DEMO_R=256 -DRMS_DEMO_DEBUG=ON
cmake --build "$BUILD_DIR" --target rms_norm_quant_story -j 4
```

`demo/CMakeLists.txt` builds only RMSNorm from the included cann-samples checkout.
It does not configure unrelated examples or require JSON downloads, asc-devkit,
shmem, submodule initialization, or network access. The JSON archive in `demo/offline/`
is retained for the upstream root CMake configuration and is unnecessary for this build.

All variants default to **128 × 256**, replacing **4096 × 8192**:
32768 elements instead of 33554432, a 1024-fold reduction in element count.
`RMS_DEMO_DEBUG=ON` adds `-g` while retaining `-O3` optimization.
Variants 0 and 1 use one Vector Core; later variants retain the original row distribution.
256 columns retain vector loops and enable the binary-add branch in variant 6.
The data generator uses seed `20260511` for identical inputs across variants.

The shape is selected at build time, not through executable arguments:

```bash
RMS_DEMO_A=128 RMS_DEMO_R=256 bash "$DEMO_ROOT/demo/build.sh"
# Restore the original shape, with substantially longer simulation time:
# RMS_DEMO_A=4096 RMS_DEMO_R=8192 bash "$DEMO_ROOT/demo/build.sh"
```

## 3. Select and run variants

```bash
bash demo.sh                       # interactive menu
bash demo.sh 2 4 5                  # selected variants without the menu
bash demo.sh --dry-run 2 4 5        # preview exact commands without simulation
bash demo.sh --list                 # list variants and descriptions
```

Enter numbers `0..6` separated by spaces. Menu commands:

- `a`: run the main sequence, 1, 2, 4, 5, 6.
- `b`: build all seven variants.
- `p 2 4`: preview commands for variants 2 and 4.
- `s`: summarize saved profiles.
- `q`: exit.

The menu returns after the selected runs finish. Choose `3 4` to isolate double buffering.
Before execution, the launcher displays CANN initialization, `CANNSIM_COLLECT`,
`BIPROF_OPTS`, `PYTHONPATH`, and the exact command for each selected variant.
Build and simulation commands are also echoed during execution with `set -x`
and saved in `logs/`. Missing binaries or a stale CMake cache trigger an offline rebuild.
Offline NumPy installation is handled by `start.sh`.

### Automatic main sequence

```bash
bash "$DEMO_ROOT/demo/run.sh"             # 1 → 2 → 4 → 5 → 6
# Run each main variant separately:
bash "$DEMO_ROOT/demo/run.sh" 1
bash "$DEMO_ROOT/demo/run.sh" 2
bash "$DEMO_ROOT/demo/run.sh" 4
bash "$DEMO_ROOT/demo/run.sh" 5
bash "$DEMO_ROOT/demo/run.sh" 6
```

Exact simulator commands without the wrapper:

```bash
source "$DEMO_ROOT/demo/env.sh"
BIN="$BUILD_DIR/Samples/2_Performance/rms_norm_quant_story"
python3 -m npusim.main record "$BIN/rms_norm_quant_1_preload_gamma" -s Ascend950 -g vf -n all -o "$RESULTS_DIR/rms_norm_quant_1_preload_gamma"
python3 -m npusim.main record "$BIN/rms_norm_quant_2_multi_core" -s Ascend950 -g vf -n all -o "$RESULTS_DIR/rms_norm_quant_2_multi_core"
python3 -m npusim.main record "$BIN/rms_norm_quant_4_double_buffer" -s Ascend950 -g vf -n all -o "$RESULTS_DIR/rms_norm_quant_4_double_buffer"
python3 -m npusim.main record "$BIN/rms_norm_quant_5_ub_utilization" -s Ascend950 -g vf -n all -o "$RESULTS_DIR/rms_norm_quant_5_ub_utilization"
python3 -m npusim.main record "$BIN/rms_norm_quant_6_binary_sum" -s Ascend950 -g vf -n all -o "$RESULTS_DIR/rms_norm_quant_6_binary_sum"
```

`-g vf` enables automatic reports and additional VF IPC JSON output.
`-n all` collects and reports all available AI cores: this configuration has
32 AI cores with vector subcores. It does not restrict computation to one core.
`CANNSIM_COLLECT=all` enables all collector groups. Timing simulation is used;
`--pv` is omitted because accurate timing is required.
Full collection and reports require more CPU time and memory than functional simulation.
For a smaller report, use `REPORT_CORES=0 bash demo/run.sh 2`; recorded demo results use `all`.

Executables invoke `gen_data.py` next to the binary. Run variants sequentially:
input and output filenames are shared within a build directory.
The numerical comparison permits an absolute int8 difference of at most 1.
Success prints `Precision is 100%` and `Compare Difference length 0`.
This is a tolerance check rather than bitwise identity. The wrapper checks the
success message because an upstream example can return zero on a mismatch.

## 4. Presentation order

1. **1 — preload_gamma:** gamma is loaded once outside the row loop.
   Show that one Vector Core is active; this is the starting point for parallelization.
2. **2 — multi_core:** independent rows are distributed across Vector Cores.
   Compare kernel duration and occupancy with variant 1; row computation is unchanged.
3. **4 — double_buffer:** compared with 2, this includes both MicroAPI VF register reuse
   and double buffering. Show VF IPC, load/store counts, and overlapping pipeline tracks.
   Use **3 → 4** to demonstrate double buffering separately.
4. **5 — ub_utilization:** batch multiple rows in UB to reduce DMA commands and scalar
   loop overhead. Each core has little work at this shape, so overlap and gains differ
   from the original large case.
5. **6 — binary_sum:** change the accumulation scheme and reciprocal-square-root
   refinement. Show VF/instruction changes and the numerical check. This step does not
   guarantee a speedup over 5.

Variants 0 and 3 are also available. For the complete source progression:
`bash demo/run.sh 0 1 2 3 4 5 6`.
Variant 0 reloads gamma for every row; 0 → 1 isolates gamma preloading.
The upstream README's large-shape results are not measurements of this small demo.
Measured results and actual hints are listed in section 6.

## 5. Report files

Each run creates `results/rms_norm_quant_<variant>/npusim_<timestamp>_<name>/`.
`record/` contains collector SQLite databases and logs; reports are under `report/results/`.
Console output and exact commands are also saved in `logs/rms_norm_quant_*.log`.
Exact artifact paths are listed in `measurements.json`.

- `summary.json`: kernel clocks, instruction counts, active cores, utilization, overlap, and diagnosis.
- `aicore_utilization.json`: activity distribution across cores and subcores.
- `core_*/trace_core*.json`: instruction/pipeline timelines and scalar/VF IPC.
  Load a file in local Chrome/Chromium at `chrome://tracing`; no Internet is required.
- `*_vf_report.json`: additional VF IPC output requested with `-g vf`.
- `*.npu-rep`: archive for a compatible report viewer, when produced by the backend.
- `.db` tables `HintTypes`, `HintMessages`, `KernelHints`, and `InstructionHints`: actual hints.

Regenerate reports from existing raw data without repeating simulation:

```bash
source demo/env.sh
RUN=/path/to/results/rms_norm_quant_2_multi_core/npusim_TIMESTAMP_NAME
python3 -m npusim.main report -e "$RUN/record" -n all -o "$RUN/report-regenerated" \
  --object-file "$BUILD_DIR/Samples/2_Performance/rms_norm_quant_story/rms_norm_quant_2_multi_core"
```

For correct source-line mapping, rebuild the executable with the same source and flags.
Viewing existing JSON does not require rebuilding. The ordinary `report` command does
not add `-g vf`; the existing VF JSON files are included in the full package.

Extract summaries and hints from completed runs, opening databases read-only:

```bash
python3 demo/summarize.py
```

This updates `measurements.json`. If the primary BiProf backend fails and falls back
to `prof_demo`, JSON reports may exist without the full hint system. Check
`report/results/runner.py.log`; missing hint records do not prove the absence of issues.
Hint processor status is also retained in the summary.

## 6. Measured results (2026-11-03)

Main sequence: **1 → 2 → 4 → 5 → 6**, shape `128 × 256`, timing simulator,
`CANNSIM_COLLECT=all`, `-g vf -n all`.
All five numerical checks passed: **100%, Compare Difference length 0**, tolerance ≤ 1.
`measurements.json` contains full metrics, artifact paths, hint messages, and processor status.

| Variant | Active subcores | Kernel clocks | CPU simulation, s | Exec IPC | RVECLD | RVECST | MTE2 / MTE3 transactions |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1_preload_gamma | 1 | 111589 | 249.28 | 0.2717 | 2948 | 3589 | 129 / 128 |
| 2_multi_core | 64 | 8788 | 42.83 | 0.2285 | 3200 | 3904 | 192 / 128 |
| 4_double_buffer | 64 | 9746 | 46.20 | 0.3289 | 1920 | 1216 | 192 / 128 |
| 5_ub_utilization | 64 | 8123 | 42.36 | 0.2228 | 1920 | 1088 | 128 / 64 |
| 6_binary_sum | 64 | 9478 | 44.92 | 0.2141 | 2112 | 1536 | 128 / 64 |

Kernel clocks describe device-kernel execution. CPU simulation time includes the
model and its startup and is a separate metric. Report generation takes additional time.
The complete main sequence with reports took about **8 minutes 18 seconds** on this machine.
Existing recorded reports can be shown immediately without repeating simulation.

| Comparison | Measured effect | Related hints |
|---|---|---|
| 1 → 2 | 12.70× fewer clocks; active vector subcores 1 → 64 | `general_single_core` and `small_grid_hint` appear in 1 and disappear in 2 |
| 2 → 4 | RVECLD −40%, RVECST −68.9%, Exec IPC 0.2285 → 0.3289; kernel clocks increase 10.9% | `low_vec_ipc_hint` and `low_vec_mte2_overlap_hint` remain below their thresholds |
| 4 → 5 | Kernel clocks −16.7%; MTE2 192 → 128, MTE3 128 → 64; scalar instructions 55808 → 53312 | `mte_calls_hint` did not fire; `general_aiv_underutilization` appears |
| 5 → 6 | Different reduction/reciprocal square root; numerical check passes; clocks increase 16.7% | The hint set remains; there is no separate accuracy-improvement hint |

Multicore variants also trigger `tail_effect_inter_core` and `tail_effect_intra_core`.
Each subcore processes only two rows, so startup and completion significantly affect its span.
This small shape demonstrates profiling mechanics but does not reproduce the monotonic
large-shape speedups in the upstream README. Comparison 2 → 4 combines VF and double buffering;
use variant 3 to separate them.

### Observed profiling limitations

- `low_vec_mte2_overlap_hint` remains in all five main variants. Relative to 2, variant 4
  improves AIV0/AIV1 overlap from 0.0670/0.0646 to 0.1610/0.1515, still below 0.20.
- `vector_fusion_hint` and `mte_calls_hint` did not emit messages in these runs.
  Counter-based observations should not be presented as hints that actually fired.
- `--memory-utilization` produced one memory view in 1 and 64 in multicore variants.
  Heatmap cell counts for 1/2/4 are 36/2304/1600. Data is stored in the DB and `.npu-rep`.
- Despite `CANNSIM_COLLECT=all`, `SIMDSamplingStats`, `VfPMUMetrics`, and `PMUScalarCounters`
  are empty in the collected data. PMU hints cannot be demonstrated from these records.
  VF IPC and instruction metrics are present.
- For MicroAPI variants, `ascend950_simd_region_tracing_analyzer` reports
  `RV_VBR instruction without Sn value`. General BiProf reports, VF JSON, memory heatmaps,
  and hint processors completed, but SIMD regions were not fully decoded.
  The packaged simulator source is unmodified.
- The target repository has no `npusim.dashboard` module, so aggregated HTML was skipped.
  Show `.npu-rep` in a compatible viewer or use JSON/Chrome tracing.
- `data_race_detection` found no violations. `sync_instruction_detection` emitted
  2443/3228/3179/1708/1780 messages for variants 1/2/4/5/6 respectively.
  Source-mapped reports are included. These messages were not investigated separately;
  passing the numerical check does not imply a clean synchronization report.

### Relocation validation

Both repositories and offline dependencies were copied to `/tmp/npusim_offline_relocation_check`.
All seven targets were rebuilt there with restricted network access and no header or package downloads.
Offline NumPy wheel installation and automatic replacement of a CMake cache from another path
were also checked. Logs: `logs/offline-relocation-build.log` and `logs/offline-stale-cache-build.log`.
The transferable package was checked for absolute symlinks; none were found.

### Isolated double-buffer comparison

Additional variant **3_vf**: 10196 kernel clocks, 45.80 s CPU simulation, numerical check 100%.
**3 → 4** changes clocks from 10196 to 9746: **4.4% fewer clocks**.
AIV0/AIV1 MTE2/VEC overlap rises from 0.0558/0.0704 to 0.1610/0.1515.
`general_aiv_underutilization` appears in 3 and disappears in 4;
`low_vec_mte2_overlap_hint` remains because overlap is still below 0.20.
Use **3 → 4**, rather than 2 → 4, to demonstrate double buffering separately.
Variant 3's recorded data is included. `start.sh` still runs the main sequence 1, 2, 4, 5, 6.

## 7. Short presenter script

1. Run `bash demo.sh` and introduce the variants.
2. Enter `p 1 2` to show exact commands and collection settings; explain `-g vf -n all`.
3. Enter `1 2` to compare single-core and multicore execution.
4. Enter `p 3 4`, then `3 4`, to compare VF with one and two buffers.
5. Enter `4 5` to show row batching in UB.
6. Enter `5 6` to show the reduction change; explain why 6 is slower at this shape.
7. Enter `s` for saved-run summaries, or `q` to exit.

To save presentation time, show the included recorded profiles and run only the variants
needed for the audience. Every run creates a new timestamped directory and preserves
previous profiles. Model timings vary slightly between runs; the table describes the
first main sequence. `measurements.json` may also contain later interactive-menu validation runs.
