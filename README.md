# NPUSim profiling demo

From a checkout, run the demo directly (Git LFS is optional):

```bash
bash start.sh 2 5             # download/unpack if needed, build, record profiles
bash start.sh build           # build all seven variants only
```

Preparing a fresh checkout requires `curl`, `tar` and `sha256sum`. The archive
download is pinned to the checked-out Git commit and verified against its checksum.

The launcher checks the archive's SHA-256 before extraction and applies the
tracked wrappers in `compatibility/demo/`. It selects the newest installed CANN
by version and build timestamp, or honors an explicit `CANN_SETENV`.
The complete build and numerical/profile checks of all seven variants passed on CANN
**9.3.0**, build **20261104000324968** (November 4), on Linux x86_64.
Other newer builds still need validation against their simulator/helper ABI.
Changing CANN preserves the old build directory and configures a fresh one.
On the tested host, variant 2 took about nine minutes with the two-core cap;
variant 5 took about two and a half minutes. Full simulation includes host-side
recording and report generation, so these times are not kernel timings.

From a repository checkout, prepare the package without building or running it:

```bash
bash prepare.sh
```

This also updates launch wrappers in a previously extracted package. Run it
after pulling repository updates. Existing saved reports remain available.

**Presentation walkthrough:** [English](DEMO_STORY.md) · [Русский](DEMO_STORY_RU.md).
Both versions cover the same four reports, 0 → 1 → 2 → 5, with narration,
exact timeline comparisons from the new recordings. Existing viewer screenshots
are explicitly historical and show the previous 32-core suite.

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

If `git lfs` is missing, install the Git LFS executable using your package manager
(`sudo apt-get install git-lfs` on Ubuntu), then run `git lfs install --local`
and `git lfs pull`. A 134-byte archive beginning with
`version https://git-lfs.github.com/spec/v1` is an LFS pointer; it cannot be
unpacked. `bash prepare.sh` downloads the payload directly from GitHub even
without Git LFS. Downloads require network access.
Git LFS is still needed when committing or pushing changes to the archive.

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
For a trace stored as `trace_core0.json.gz`, decompress a copy first with
`gzip -dk trace_core0.json.gz`.

## Requirements and exact versions

Viewing the saved reports does not require CANN or a rebuild. For building and
recording, the host needs Linux x86_64, CMake, make, a C/C++ compiler, and the matching CANN
installation with Ascend950/dav-3510 timing-simulator support. A physical NPU is
unnecessary. Python and NumPy are bundled; building and recording from the
extracted package need no pip installation, Git, Git LFS, or network access once
the host requirements are installed.

| Component | Tested version / upstream base | Download or source |
| --- | --- | --- |
| CANN | **9.3.0**, internal version `V100R001C13B046`, build `20261104000324968` | [Matching Huawei build](https://ascend.devcloud.huaweicloud.com/artifactory/cann-run-mirror/software/master/20261104000324968/) · [CANN download portal](https://www.hiascend.com/developer/download/community/result?module=cann) |
| npu-simulator | `1185ddf016a0e3563c0d3af80305d7ea78c81fe9` | [Exact commit](https://gitcode.com/cann/npu-simulator/commit/1185ddf016a0e3563c0d3af80305d7ea78c81fe9) |
| cann-samples | `5c6e28cc7fce6fbeb9b67befcde98a6a4dc492ed` | [Exact commit](https://gitcode.com/cann/cann-samples/commit/5c6e28cc7fce6fbeb9b67befcde98a6a4dc492ed) |

Install the x86_64 CANN toolkit and 950 ops packages from the matching build.
The Git hashes are upstream base revisions. The bundled sources include demo
modifications: the 128 × 256 shape, offline build/launch wrappers, and the fix
for empty RV_VBR register payloads. Use the bundled sources to reproduce the reports.

CANN is auto-detected, including when several installations exist. Existing
checkouts can update their wrappers with `bash prepare.sh`; the new archive
already includes them. To select a specific build:

```bash
export CANN_SETENV=/actual/path/to/cann/bin/setenv.bash
```

For the newer installation tested here:

```bash
CANN_SETENV=/usr/local/Ascend/20261104000324968/cann-9.3.0/x86_64-linux/bin/setenv.bash bash start.sh 2 5
```

This command works from either the repository root or the prepared package.
All seven saved profiles in the current archive were recorded on November 5
using the November 4 CANN build. The archive excludes the old recordings.
[recording-manifest.json](NPUSim_Prof_Live_Demo/recording-manifest.json) contains
the exact run paths, report hashes, launch/collection scope and guard settings.
The bundled NPUSim sources work with this helper without an ABI patch.

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
Each run checks the output with absolute int8 tolerance 1. Variants 0 and 1
intentionally launch and record one vector core. Variants 2–6 launch up to
**32 AIV lanes** (`RMS_DEMO_CORES=32`) and record with `REPORT_CORES=all` by default.
The 32 AIV lanes appear as 16 physical core IDs, each with AIV0 and AIV1;
verify `ai_core_active=32` and both core types in the recorded database.
`CANNSIM_COLLECT=all` selects collection categories, not the number of cores.
The old October 28 screenshots are only UI illustrations; use the linked
November 5 reports for current measurements.
New runs have timestamped folders.

Local recording uses two CPU affinity slots, two model worker threads and one
report worker. `demo/limited_run.py` monitors the entire subprocess tree, including
new sessions, every 0.1 seconds. It kills that tree above 12288 MiB (12 GiB) aggregate RSS,
below 1536 MiB available host memory, or at the per-variant timeout: 3600 seconds
for single-core variants 0 and 1, 900 seconds for variants 2–6. Set
`DEMO_TIMEOUT_SECONDS` to override either default. These are monitored
limits, not a kernel memory quota; brief overshoot is possible. Build parallelism
defaults to two jobs (`JOBS=2`).

The current recordings were made on Ubuntu 22.04 x86_64 with about 15 GiB of
host RAM. The earlier 256 × 1024 WSL2 memory-limit experiment is not a completed
profile in this archive. `start.sh` uses the 128 × 256 demo shape.

For an isolated small-shape experiment (still subject to the memory guard):

```bash
export BUILD_DIR="$PWD/.development/build-small-overlap"
export RESULTS_DIR="$PWD/.development/results-small-overlap"
RMS_DEMO_A=256 RMS_DEMO_R=1024 RMS_DEMO_CORES=2 bash start.sh 2 5 6
```

Double buffering is introduced in **3 → 4**. The **2 → 5** comparison also changes
the vector implementation and batches rows in UB. Check the recorded overlap
values and emitted hints in each new report. A convincing overlap experiment
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
  -s Ascend950 -g vf -n all -o "$RESULTS_DIR/rms_norm_quant_5_ub_utilization"
```

Regenerate a report from a saved record without running the simulator again:

```bash
source demo/env.sh
RUN="$DEMO_ROOT/results/rms_norm_quant_5_ub_utilization/npusim_20261105121436_rms_norm_quant_5_ub_utilization"
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
| `recording-manifest.json` | Current seven runs, settings and report SHA-256 hashes |

A successful numerical check does not mean synchronization detectors found no
issues. Their findings and collector limitations remain visible in `RESULTS.html`.

Git stores one LFS archive, documentation, and the preparation/compatibility
scripts. The extracted directory is
ignored to avoid duplicating the runtime and profiles in Git. Documentation
links to extracted artifacts resolve after unpacking the archive.
