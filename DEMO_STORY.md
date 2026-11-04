# From a visible problem to a verified improvement

**Four reports, 7–9 minutes: 0 → 1 → 2 → 5.** Open the saved `.npu-rep` files in the
Ascend profiling report viewer before the talk. Each transition follows the same
pattern: find a problem in the report, change the implementation, then check the
next report for the expected change.

We use the same RMSNorm + quantization workload, **128 × 256**, throughout.
All four numerical checks pass with the original absolute int8 tolerance of 1.
The times below are simulated kernel clocks, not the host time spent generating a profile.

| Report | Kernel clocks | What this stop demonstrates |
| --- | ---: | --- |
| 0 — naive | 112,429 | Repeated input transfers inside the row loop |
| 1 — preload gamma | 111,498 | Redundant gamma transfers removed; single-core hint remains |
| 2 — multi-core | 8,785 | Work distributed; Small Grid / Single-core hints disappear |
| 5 — batch rows in UB | 7,744 | Fewer VF dispatches and transfers per subcore |

## First transition: repeated copies on the timeline → load gamma once

**Before: report 0, Timeline → core 0 → AIV0; expand MTE2 and vector/VF lanes.**
Zoom into several consecutive rows, past initialization. Point out the repeating
input-transfer pattern before each row's computation.

“Here the work repeats row by row. The input row changes, but gamma is shared by
all rows. In the baseline we load both of them again on every iteration. The
trace shows the repeated transfers; the `Process()` loop identifies which one
is redundant: `CopyInGamma()` sits next to `CopyInX(loop)` inside the row loop.”

**After: report 1, the same core, lanes, and number of rows.** Include the beginning
of the trace to show the one-time gamma preload, then compare a steady-state section.

“We move gamma outside the loop. The recurring gamma transfer disappears: only
the changing input row needs to be loaded each time. The report confirms the
change: input-transfer transactions fall from **256 to 129** — 128 input rows
plus one gamma load — while output transfers remain at 128. We removed redundant
work without changing the result.”

Time falls slightly, by **0.8%**. This stop demonstrates elimination of repeated
traffic; the much larger opportunity becomes clear in the next view.
The recorded transfer parameters are empty, so do not claim that the event's
Details reveal identical source addresses. Identify gamma from the source loop
and validate the change using the pattern and transaction count.

> **Screenshot 1 — before:** report 0, core 0 / AIV0, roughly 4.4–8.8 µs. Keep MTE2, PUSHQ, RVECLD, and RVECST visible. Mark the repeated MTE2 pairs, then the recurring vector load/store groups.
>
> **Screenshot 2 — after:** report 1, the same 4.4–8.8 µs scale and lanes. Mark the one-time preload and the single recurring row transfer. Add an inset of the initial gamma-conversion VF and its one-time stores.

For a second visual check, follow **RVECLD → RVECST**, rather than stopping at
MTE2: gamma no longer needs the same repeated conversion and UB writeback in every
row. Pure `RV_VST` events on core 0 / AIV0 fall from **3,328 to 2,820**;
`PUSH_PB` argument-setup events fall from **640 to 513**. The repeated per-row
sequence loses work on several lanes, not just one copy. Gamma conversion becomes
an initial one-time VF; the total VF count actually changes from 384 to 385, so
do not describe this transition as eliminating VF calls.

Source comparison: [0_naive.asc](NPUSim_Prof_Live_Demo/cann-samples/Samples/2_Performance/rms_norm_quant_story/src/0_naive.asc)
and [1_preload_gamma.asc](NPUSim_Prof_Live_Demo/cann-samples/Samples/2_Performance/rms_norm_quant_story/src/1_preload_gamma.asc), `Process()`.

## Second transition: a single-core hint → distribute the independent rows

**Before: report 1, Performance hints; then zoom out on Timeline.**

“We have cleaned up the transfers, but almost the entire processor is still idle.
The Small Grid hint says **only 1 of 32 available cores is used**, and the
Single-core hint recommends distributing the work. The timeline supports that
message: one vector context carries the execution. Rows are independent, so we
can assign different rows to different vector subcores.”

**After: report 2, Performance hints and the multicore Timeline overview.**

“Now the timeline shows work across the cores. More importantly, the two messages
that led us here — `small_grid_hint` and `general_single_core` — are **absent**.
Those rules still completed successfully; the problem that triggered them is
no longer present. Kernel time falls from 111,498 to **8,785 clocks**, about
**12.7× faster**.”

There are 32 physical AI cores, each with AIV0 and AIV1. The summary's
`ai_core_active=64` describes the 64 active vector contexts in this run, not
64 physical AI cores. Other hints remain: Low SIMD IPC, low VEC/MTE2 overlap,
and Tail Effect. We have fixed the launch parallelism; now we look inside a core.

> **Screenshot 3 — before:** report 1, Timeline overview plus Small Grid / Single-core hints. Show the full long row sequence, with the time-axis range visible; add a core-0 closeup showing the repeating three-VF row motif.
>
> **Screenshot 4 — after:** report 2, the full multicore Timeline and the hint list without those messages. In a second crop, keep core 0 / AIV0: the three-VF row motif now repeats twice, rather than 128 times.

There is a concrete timeline change even when we stay on core 0: **128 output
transfers become two**, and **385 VF executions become seven** (one gamma VF plus
three per row). We remove the long serialized chain from one context by spreading
it across 64 vector contexts; the row's computational motif itself is still
recognizable. Use the `.npu-rep` multicore view for the overview: a standalone
`core_0` JSON cannot show the other cores. Keep equal time scales for the local
comparison, or show both axis ranges explicitly when using Fit.

## Third transition: fragmented per-row work → a larger unit of work

**Before: report 2, Timeline → core 0 → AIV0 → PUSHQ / VF events, MTE2, and MTE3.**
Use the full execution window of that subcore, excluding initialization where possible.

“Parallelism is fixed, but the work inside each subcore is still fragmented.
Each subcore handles two rows in this small example. On core 0 / AIV0 we can count
**seven VF executions**: one for gamma preparation, then three per row.
The rows also arrive and leave through separate transfers. The report is showing
us the granularity of the implementation, not just its final duration.”

**After: report 5, exactly the same core and component.**

“In the final version we combine the vector computation and batch rows in UB.
The same two rows now need only **two VF executions** on this subcore: gamma
preparation and the batched computation. The VF sequence on the timeline is
visibly simpler. Across the whole kernel, VF executions fall from **448 to 128**,
and intermediate vector stores from **3,904 to 1,088**.”

“Transfers are also grouped. On core 0 / AIV0, input transfers go from three to
two — gamma plus two separate rows becomes gamma plus one batch — and output
transfers go from two to one. In the architecture metrics this corresponds to
**96 → 64 input transactions and 64 → 32 output transactions per AIV side**,
aggregated across the 32 physical cores. Kernel time falls to **7,744 clocks**,
another **11.8%** improvement.”

This comparison combines MicroAPI computation, double buffering, and row batching;
it does not isolate the contribution of each change. Reports 3 and 4 remain in
the package for a deeper technical discussion, but are not stops in this walkthrough.
Do not attribute the entire improvement to batching or claim that every individual
change necessarily accelerated this small workload.

> **Screenshot 5 — before:** report 2, core 0 / AIV0, approximately 4.4–6.8 µs. Show PUSHQ, RVECLD, RVECST, MTE2, and MTE3. Mark seven VF calls, two row-compute groups, and the separate output copies.
>
> **Screenshot 6 — after:** report 5, the same lanes and 4.4–6.8 µs scale. Mark the gamma VF, the one batched-compute VF, and the single output transfer. Do not confuse fewer, larger work groups with elimination of the computation itself.

Take a second, tighter look at the **RVECLD / RVECST** lanes. In report 2, the
row groups repeatedly spill vector results to UB and read intermediates back.
In report 5, more intermediates remain inside the combined VF. On this exact
core/subcore, pure `RV_VST` events fall from **48 to 14**, `RV_VLD` from **40 to 30**,
and all **10 `RV_VLDI` events disappear**. Search `RV_VLDI` in each report and
compare the small load islands with the much sparser store lane. This is the
instruction-level evidence behind the combined-computation explanation.

On the same RVECST lane, **four `RV_SMEM_BAR` events become one**, and **seven
`RV_SEND` markers become two**. These are fewer internal memory-barrier and
VF-completion markers around the reorganized computation. Show those individual
events in Details; do not describe them as proof that all synchronization stalls
or data dependencies disappeared.

> **Screenshot 7 — vector detail before:** report 2, core 0 / AIV0, 5.7–6.5 µs; highlight `RV_VLDI`, repeated `RV_VST` clusters, and the four `RV_SMEM_BAR` events.
>
> **Screenshot 8 — vector detail after:** report 5, 5.9–6.2 µs; highlight the shorter store sequence and the single `RV_SMEM_BAR`. Mention that `RV_VLDI` has no events in this version. These two detail crops use different ranges; label their axes and compare event structure/counts, not rectangle widths.

As a short final view, open **Memory load analysis → Full screen → UB** in report 5.
Connect the grouped transfers to the OUT→UB and UB→OUT paths and the touched UB
addresses. The heatmap is address coverage, not time occupancy or proof of bandwidth
saturation. Low IPC, low overlap, and some tail hints still exist in this report;
the visual improvement here is the reduced fragmentation, not disappearance of
those hints.

> **Optional screenshot 9:** report 5, memory topology and UB address-coverage heatmap.

“We have followed the evidence through three changes: remove repeated traffic,
use the available cores, and give each subcore a larger unit of work. The final
version is about **14.5× faster than the baseline** on this workload. In each
comparison we can point to the specific trace pattern or hint that changed.”

## Timeline capture sheet — presenter reference

The lane names below are from the saved core-0 Chrome traces. The report viewer
may shorten the labels; match the `AIV0_…` prefix. `PUSHQ_DISPATCH` is a separate
producer track: count execution events named exactly **`VF` on `AIV0_PUSHQ`**.
For DMA, count **`MOV_SRC_TO_DST_ALIGNv2`**, not the initial `MOV_SPR_XN` setup.
For vector stores, **`RV_VST`** is one mnemonic, whereas **RVECST** is the entire
lane and also includes `RV_SEND`, `RV_SMEM_BAR`, and other instructions.

All counts here are **core 0 / AIV0**, not global totals:

| Lane / event | Report 0 | Report 1 | Visual point |
| --- | ---: | ---: | --- |
| MTE2 / `MOV_SRC_TO_DST_ALIGNv2` | 256 | 129 | Recurring pairs become a one-time preload plus single row loads |
| PUSHQ / `PUSH_PB` | 640 | 513 | Less repeated argument/setup work |
| RVECST / `RV_VST` | 3,328 | 2,820 | Less repeated vector writeback |
| PUSHQ / `VF` | 384 | 385 | Gamma conversion moves to a one-time call; VF count is not the win |

For the MTE2 screenshot, select a copy and check **Details → Parameter → pc**.
In report 0 the two repeating sites are **`0xd20` and `0xde0`**, 128 executions
each. In report 1, **`0xa94` executes once** and **`0xe5c` executes 128 times**.
This distinguishes the two call sites even though every copy has the same name
and the recorded `arguments` field is empty. PCs belong to each binary: do not
expect an instruction to keep the same PC after recompilation.

| Lane / event | Report 1 | Report 2 | Visual point |
| --- | ---: | ---: | --- |
| MTE2 / `MOV_SRC_TO_DST_ALIGNv2` | 129 | 3 | Only two input rows plus gamma remain on this context |
| MTE3 / `MOV_SRC_TO_DST_ALIGNv2` | 128 | 2 | Long output-copy comb collapses to two teeth |
| PUSHQ / `VF` | 385 | 7 | Same row motif, far fewer serial repetitions per context |

| Lane / event | Report 2 | Report 5 | Visual point |
| --- | ---: | ---: | --- |
| PUSHQ / `VF` | 7 | 2 | Multiple short VF groups become gamma + batched computation |
| PUSHQ / `PUSH_PB` | 9 | 4 | Fewer argument-setup events around VF calls |
| MTE2 / `MOV_SRC_TO_DST_ALIGNv2` | 3 | 2 | Two separate row loads become one batch load |
| MTE3 / `MOV_SRC_TO_DST_ALIGNv2` | 2 | 1 | Two output-copy events become one |
| RVECLD / `RV_VLD` | 40 | 30 | Fewer vector loads |
| RVECLD / `RV_VLDI` | 10 | 0 | Intermediate-load islands disappear |
| RVECST / `RV_VST` | 48 | 14 | Intermediate-store groups become sparser |
| RVECST / `RV_SMEM_BAR` | 4 | 1 | Fewer internal memory-barrier markers |
| RVECST / `RV_SEND` | 7 | 2 | Fewer VF-end markers |

Useful anchors in the exact saved traces:

| Report | Event | Raw trace timestamp, µs |
| --- | --- | ---: |
| 0 | First MTE2 pair, PCs `0xd20` / `0xde0` | 4.729697 / 4.760606 |
| 1 | One-time MTE2 site `0xa94`; first recurring `0xe5c` | 4.753333 / 4.807879 |
| 2 | First `RV_VLDI` island | 5.761818–5.762424 |
| 2 | Four `RV_SMEM_BAR` markers | 6.005455, 6.020606, 6.449697, 6.464848 |
| 5 | Batched-compute `VF`, PC `0xea4` | 5.912727 |
| 5 | Only `RV_SMEM_BAR`, PC `0x10cc` | 6.099394 |
| 5 | Only MTE3 output copy | 6.180606 |

These are Chrome Trace `ts` values in **microseconds**; a nanosecond axis shows
1,000 times these numbers. If the viewer rebases its origin, locate the event by
name and PC instead. Exact timestamps/PCs apply to the linked saved runs, not
necessarily to a rebuild. Keep only the lanes needed for the comparison visible;
scalar slot tracks can otherwise hide the pattern.

**Do not point at arbitrary whitespace and call it a stall.** These records have
no dedicated BUBBLE events or explicit `WAIT_FLAG` events. They support showing
fewer copies, spill/load islands, barriers, and dispatches, but not claiming that
all waits vanished or that every empty interval has a known cause. The
low-overlap hint still exists in report 5; do not use this pair to claim that
copy/compute overlap became perfect.

## Viewer and tested environment

To view `.npu-rep` reports, download the VS Code extension (`.vsix`) from
[the profiling extension releases](https://gitcode.com/opdevtools/plugin_release/releases/). In VS Code, open **Extensions →
… → Install from VSIX…**, select the downloaded file, and open/import the saved
`.npu-rep` in the extension's profiling report viewer. This displays the Timeline,
Details, Performance hints, and memory/compute analysis used in this walkthrough.
You can view the saved reports without rerunning the simulation.

The equivalent extension-install command is:

```bash
code --install-extension /path/to/downloaded-extension.vsix
```

The demo was built and recorded with these exact versions:

| Component | Tested version / upstream base revision | Download or source |
| --- | --- | --- |
| CANN | **9.3.0**, internal version `V100R001C13B036`, build `20261028000328247`; Linux x86_64, Ascend950 / dav-3510 | [Matching Huawei build](https://ascend.devcloud.huaweicloud.com/artifactory/cann-run-mirror/software/master/20261028000328247/) · [CANN download portal](https://www.hiascend.com/developer/download/community/result?module=cann) |
| npu-simulator | `1185ddf016a0e3563c0d3af80305d7ea78c81fe9` | [Exact commit](https://gitcode.com/cann/npu-simulator/commit/1185ddf016a0e3563c0d3af80305d7ea78c81fe9) |
| cann-samples | `5c6e28cc7fce6fbeb9b67befcde98a6a4dc492ed` | [Exact commit](https://gitcode.com/cann/cann-samples/commit/5c6e28cc7fce6fbeb9b67befcde98a6a4dc492ed) |

The matching build directory contains
`Ascend-cann-toolkit_9.3.0~weekly.20261028.01_linux-x86_64.run` and the corresponding
`Ascend-cann-950-ops_9.3.0~weekly.20261028.01_linux-x86_64.run`.
Use the matching Ascend950 timing-simulator support; the simulator/helper data
contract for this demo is version **7**.

The two Git hashes identify the upstream base revisions. The archive includes
local demo changes: the small 128 × 256 shape, offline build/launch wrappers,
and the simulator fix for empty RV_VBR register payloads. Use the bundled sources
to reproduce these reports. Python 3.12.16 and NumPy 1.26.4 are already bundled.

## Commands: prepare before the presentation

The saved reports can be shown immediately. To reproduce the four stops:

```bash
cd /home/lxchu/Projects/CANN/NPUSim_PerfDemo_20260511/NPUSim_Prof_Live_Demo

# Build and record the four presentation examples. No menus or prompts.
# The first two are slow single-core simulations; run them before the talk.
bash start.sh 0 1 2 5

# Alternatively, build and run all seven examples.
bash start.sh

# Rerun one comparison or build without recording.
bash start.sh 2 5
bash start.sh build
bash start.sh --list

# Refresh measurements.json, latest-measurements.json, and RESULTS.html.
runtime/python/bin/python3 demo/summarize.py
```

Python and NumPy are bundled. The host needs CANN 9.3.0 with the Ascend950/dav-3510
simulator, CMake, make, and a C/C++ compiler; a physical NPU is unnecessary.
CANN is auto-detected. If there are several installations, select one before running:

```bash
export CANN_SETENV=/actual/path/to/cann/bin/setenv.bash
```

The wrappers collect all groups and enable VF reports and all AI cores.
The equivalent direct command for the final example is:

```bash
source demo/env.sh
export CANNSIM_COLLECT=all
export BIPROF_OPTS='-l debug --save_tmp_files --scalar-ipc --vec-ipc --simd-perf --memory-utilization'
python3 -m npusim.main record \
  "$BUILD_DIR/Samples/2_Performance/rms_norm_quant_story/rms_norm_quant_5_ub_utilization" \
  -s Ascend950 -g vf -n all -o "$RESULTS_DIR/rms_norm_quant_5_ub_utilization"
```

To regenerate a report from saved raw data without repeating simulation:

```bash
source demo/env.sh
RUN="$DEMO_ROOT/results/rms_norm_quant_5_ub_utilization/npusim_20261103215316_rms_norm_quant_5_ub_utilization"
python3 -m npusim.main report -e "$RUN/record" -n all -o "$RUN/report-regenerated"
```

Keep the original report for this walkthrough: its extra VF JSON is produced by
the recording's `-g vf`, not by the standalone report command.

## Files to open

Import the following `.npu-rep` files into the Ascend profiling report viewer.
These are the exact runs behind the numbers and screenshot instructions above.
For new runs, current paths are listed in `latest-measurements.json`.

| Stop | Saved report |
| --- | --- |
| 0 — 0_naive | [Open .npu-rep](NPUSim_Prof_Live_Demo/results/rms_norm_quant_0_naive/npusim_20261103211811_rms_norm_quant_0_naive/report/results/0000_rms_norm_quant_reports/0000_rms_norm_quant.npu-rep) |
| 1 — 1_preload_gamma | [Open .npu-rep](NPUSim_Prof_Live_Demo/results/rms_norm_quant_1_preload_gamma/npusim_20261103213408_rms_norm_quant_1_preload_gamma/report/results/0000_rms_norm_quant_reports/0000_rms_norm_quant.npu-rep) |
| 2 — 2_multi_core | [Open .npu-rep](NPUSim_Prof_Live_Demo/results/rms_norm_quant_2_multi_core/npusim_20261103214712_rms_norm_quant_2_multi_core/report/results/0000_rms_norm_quant_reports/0000_rms_norm_quant.npu-rep) |
| 5 — 5_ub_utilization | [Open .npu-rep](NPUSim_Prof_Live_Demo/results/rms_norm_quant_5_ub_utilization/npusim_20261103215316_rms_norm_quant_5_ub_utilization/report/results/0000_rms_norm_quant_reports/0000_rms_norm_quant.npu-rep) |

[RESULTS.html](NPUSim_Prof_Live_Demo/RESULTS.html) is the offline comparison and artifact index. A linked
`core_0/trace_core0.json` can also be loaded in Chromium at `chrome://tracing`, but
that viewer does not display the Performance hints dock.

## Presenter notes

The supported screens are **Timeline / Details**, **Performance hints**,
**Compute load analysis**, and **Memory load analysis**, as described in the
feature reference `asc-vscode-draft/profiling_report_guide.md`. For IPC, select a
VF event and inspect `exec_ipc`, `scalar_ipc`, and `load_store_ipc` in **Details →
Parameter** when attached; there is no separate VF IPC chart in that viewer.

The report manifests contain kernel hints, VF IPC, and memory-heatmap data.
They have no VF PMU counters, SIMD stall-sampling rows, or bubble rows; do not
promise PMU-based hints or BUBBLE lanes in these recordings. `HintPassed=1`
means a rule ran, not that a message was emitted. Source-line hints are empty.
[Source rationale](NPUSim_Prof_Live_Demo/cann-samples/Samples/2_Performance/rms_norm_quant_story/README.md)
explains the implementations; its large-shape benchmark is not our measurement.
[Full validation and detector findings](NPUSim_Prof_Live_Demo/FULL_RUN.md) are separate from this
presentation's successful numerical checks.
