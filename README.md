# NPUSim profiling demo

**Presentation walkthrough:** [English](DEMO_STORY.md) · [Русский](DEMO_STORY_RU.md).
Both versions cover the same four reports, 0 → 1 → 2 → 5, with narration,
exact timeline comparisons, and real web-viewer screenshots.

## Download and extract

The complete package is **NPUSim_Prof_Live_Demo.tar.gz**. It contains all seven
examples, their source trees, saved profiles, English and Russian walkthroughs,
and Python 3.12.16 with NumPy 1.26.4. No separate update archive is needed.

With Git and Git LFS installed, retrieve the archive with explicit download progress:

```bash
git lfs install
GIT_LFS_SKIP_SMUDGE=1 git clone https://github.com/alexChurkin/NPUSim_PerfDemo_20260511.git
cd NPUSim_PerfDemo_20260511
git -c lfs.forceprogress=true lfs pull
```

From the directory containing the archive and checksum:

```bash
sha256sum -c NPUSim_Prof_Live_Demo.tar.gz.sha256
tar -xzf NPUSim_Prof_Live_Demo.tar.gz
cd NPUSim_Prof_Live_Demo
```

If you are already reading this inside the extracted package, start below.

## View the saved reports

Open **[RESULTS.html](NPUSim_Prof_Live_Demo/RESULTS.html)** in a browser for the offline comparison,
artifact links, numerical checks, and detector findings. No simulation is needed.

You can open `.npu-rep` reports directly in the browser with the
[web profiling report viewer](https://profiling-report.vercel.app/): open the site and select/import a saved
`.npu-rep` file from the extracted demo. The web viewer is an alternative to
installing the VS Code extension.

To view reports in VS Code, download the `.vsix` from
[the profiling extension releases](https://gitcode.com/opdevtools/plugin_release/releases/).
In VS Code use **Extensions → … → Install from VSIX…**, then open/import the
saved `.npu-rep` in the extension's profiling report viewer. It provides Timeline,
Details, Performance analysis (hints), and memory/compute analysis. Alternatively:

```bash
code --install-extension /path/to/downloaded-extension.vsix
```

In the web viewer, choose **en** for English labels. To open hints, click
**Performance analysis** at the top right of **Report statistics**; messages
appear in the bottom **Performance analysis** panel. For memory coverage, open
**Memory load analysis → full-screen icon → Memory topology**, then click the
**UB** block or its tab on the right. The saved RMSNorm profiles contain heatmap
data only for UB; the other memory tabs are viewer capabilities, not additional
recorded datasets in these examples.

The walkthroughs link the exact four reports to use. For a standalone timeline,
load a `core_0/trace_core0.json` in Chromium at `chrome://tracing`; that viewer does
not provide the Performance analysis panel.

## Requirements and exact versions

Viewing the saved reports does not require CANN or a rebuild. For building and
recording, the host needs Linux x86_64, CMake, make, a C/C++ compiler, and the matching CANN
installation with Ascend950/dav-3510 timing-simulator support. A physical NPU is
unnecessary. Python and NumPy are bundled; building and recording from the
extracted package need no pip installation, Git, Git LFS, or network access once
the host requirements are installed.

| Component | Tested version / upstream base | Download or source |
| --- | --- | --- |
| CANN | **9.3.0**, internal version `V100R001C13B036`, build `20261028000328247`; simulator/helper contract **7** | [Matching Huawei build](https://ascend.devcloud.huaweicloud.com/artifactory/cann-run-mirror/software/master/20261028000328247/) · [CANN download portal](https://www.hiascend.com/developer/download/community/result?module=cann) |
| npu-simulator | `1185ddf016a0e3563c0d3af80305d7ea78c81fe9` | [Exact commit](https://gitcode.com/cann/npu-simulator/commit/1185ddf016a0e3563c0d3af80305d7ea78c81fe9) |
| cann-samples | `5c6e28cc7fce6fbeb9b67befcde98a6a4dc492ed` | [Exact commit](https://gitcode.com/cann/cann-samples/commit/5c6e28cc7fce6fbeb9b67befcde98a6a4dc492ed) |

The matching build contains
`Ascend-cann-toolkit_9.3.0~weekly.20261028.01_linux-x86_64.run` and
`Ascend-cann-950-ops_9.3.0~weekly.20261028.01_linux-x86_64.run`.
The Git hashes are upstream base revisions. The bundled sources include demo
modifications: the 128 × 256 shape, offline build/launch wrappers, and the fix
for empty RV_VBR register payloads. Use the bundled sources to reproduce the reports.

CANN is auto-detected. If several installations exist, select the matching one:

```bash
export CANN_SETENV=/actual/path/to/cann/bin/setenv.bash
```

## Build and run

Run these commands from the extracted `NPUSim_Prof_Live_Demo` directory:

```bash
bash start.sh                 # build and run all seven variants, 0 through 6
bash start.sh 0 1 2 5         # the four presentation examples
bash start.sh 2 5             # selected comparison only
bash start.sh build           # build only
bash start.sh --list          # print variant descriptions and exit
```

No menus or prompts. Progress appears in the console; detailed commands and
output go to `logs/`. Single-core variants 0 and 1 take many minutes each, so
prepare recordings before the talk. The default shape is **128 × 256**.
Each run checks the output with absolute int8 tolerance 1. New local builds launch
at most **2 vector cores** (`RMS_DEMO_CORES=2`); reports collect **core 0** by default
(`REPORT_CORES=0`). `CANNSIM_COLLECT=all` selects collection categories, not the
number of cores. Saved presentation reports above were recorded with 32 AI cores;
new recordings with this cap have different timings and parallelism hints.
New runs have timestamped folders.

Local recording uses two CPU affinity slots, two model worker threads and one
report worker. `demo/limited_run.py` monitors the entire subprocess tree, including
new sessions, every 0.1 seconds. It kills that tree above 12288 MiB (12 GiB) aggregate RSS,
below 1536 MiB available host memory, or after 900 seconds. These are monitored
limits, not a kernel memory quota; brief overshoot is possible. Build parallelism
defaults to two jobs (`JOBS=2`).

The current WSL2 environment exposes about 7.5 GiB RAM through `/proc/meminfo`,
although the physical PC has 16 GiB. With the current 12 GiB RSS cap, the
**256 × 1024** trial was stopped by the free-memory reserve at 4429 MiB during
model initialization, before kernel execution. See
`logs/rms_norm_quant_6_binary_sum_20261104_115133.log` in the extracted workspace.
No completed report or disappearing overlap warning is claimed for that trial.
The 4096 × 8192 development build is not used by `start.sh`.

To allocate 12 GiB to WSL2, add `memory=12GB` under `[wsl2]` in the Windows
`%UserProfile%\.wslconfig`, save work in WSL, run `wsl --shutdown` in PowerShell,
and reopen Ubuntu. The simulator RSS cap does not change the WSL2 VM allocation.

For an isolated small-shape experiment (still subject to the memory guard):

```bash
export BUILD_DIR="$PWD/.development/build-small-overlap"
export RESULTS_DIR="$PWD/.development/results-small-overlap"
RMS_DEMO_A=256 RMS_DEMO_R=1024 RMS_DEMO_CORES=2 bash start.sh 2 5 6
```

Double buffering is introduced in **3 → 4**. The **2 → 5** comparison also changes
the vector implementation and batches rows in UB. The saved 128 × 256 reports
retain the Low VEC/MTE2 overlap warning in every variant. A convincing experiment
must have multiple UB batches per core and measured overlap of at least 0.20;
removing the warning by having too few instructions is not evidence of overlap.

Refresh the comparison after additional runs:

```bash
runtime/python/bin/python3 demo/summarize.py
```

For a direct simulator command, after building:

```bash
source demo/env.sh
export CANNSIM_COLLECT=all
export BIPROF_OPTS='-l debug --save_tmp_files --scalar-ipc --vec-ipc --simd-perf --memory-utilization -j 1'
python3 "$DEMO_ROOT/demo/limited_run.py" python3 -m npusim.main record \
  "$BUILD_DIR/Samples/2_Performance/rms_norm_quant_story/rms_norm_quant_5_ub_utilization" \
  -s Ascend950 -g vf -n 0 -o "$RESULTS_DIR/rms_norm_quant_5_ub_utilization"
```

Regenerate a report from a saved record without running the simulator again:

```bash
source demo/env.sh
RUN="$DEMO_ROOT/results/rms_norm_quant_5_ub_utilization/npusim_20261103215316_rms_norm_quant_5_ub_utilization"
python3 -m npusim.main report -e "$RUN/record" -n all -o "$RUN/report-regenerated"
```

The bundled standalone `report` command exports VF JSON by default. It analyzes
the saved record without rerunning the kernel; the original reports used by the
walkthrough remain available alongside the regenerated output.

## Files

| Path | Contents |
| --- | --- |
| [DEMO_STORY.md](DEMO_STORY.md) / [DEMO_STORY_RU.md](DEMO_STORY_RU.md) | English / Russian narration and screenshot positions |
| [RESULTS.html](NPUSim_Prof_Live_Demo/RESULTS.html) | Comparison, report links, validation and diagnostic findings |
| `latest-measurements.json` / `measurements.json` | Machine-readable measurements and hints |
| `results/` | Raw SQLite recordings and generated reports |
| `logs/` | Build and per-variant command/output logs |
| `cann-samples/Samples/2_Performance/rms_norm_quant_story/src/` | Sources for variants 0 through 6 |
| `versions.txt` | Build and source provenance |

A successful numerical check does not mean synchronization detectors found no
issues. Their findings and collector limitations remain visible in `RESULTS.html`.

Git stores one LFS archive and these three documents. The extracted directory is
ignored to avoid duplicating the runtime and profiles in Git. Documentation
links to extracted artifacts resolve after unpacking the archive.
