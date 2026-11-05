# From repeated traffic to batched computation — new CANN recordings

[Русская версия](DEMO_STORY_RU.md) · [Setup](README.md) · [Offline results](NPUSim_Prof_Live_Demo/RESULTS.html)

**Four stops, 7–9 minutes: 0 → 1 → 2 → 5.** These reports were recorded on
November 5, 2026 with CANN **9.3.0 / V100R001C13B046**, build **20261104000324968**.
The shape is **128 × 256**, the target is Ascend950/dav-3510, and all seven
numerical checks pass with absolute int8 tolerance 1.

Variants 0 and 1 intentionally launch and record one vector core. Variants 2–6
launch all **32 AIV lanes** and record with `--core-id all`. The database has
16 physical core IDs, each with AIV0 and AIV1; the report has 16 per-core trace
files and `ai_core_active=32`. The VF totals below span all active AIV lanes;
the timeline event table further down is explicitly for core 0 / AIV0.

| Variant | Kernel clocks | Active AIV | VF total | VF / AIV | .npu-rep |
| --- | ---: | ---: | ---: | ---: | --- |
| 0_naive | 112,319 | 1 | 384 | 384 | [Open](NPUSim_Prof_Live_Demo/results/rms_norm_quant_0_naive/npusim_20261105092401_rms_norm_quant_0_naive/report/results/0000_rms_norm_quant_reports/0000_rms_norm_quant.npu-rep) |
| 1_preload_gamma | 111,462 | 1 | 385 | 385 | [Open](NPUSim_Prof_Live_Demo/results/rms_norm_quant_1_preload_gamma/npusim_20261105094102_rms_norm_quant_1_preload_gamma/report/results/0000_rms_norm_quant_reports/0000_rms_norm_quant.npu-rep) |
| 2_multi_core | 8,789 | 32 | 416 | 13 | [Open](NPUSim_Prof_Live_Demo/results/rms_norm_quant_2_multi_core/npusim_20261105121908_rms_norm_quant_2_multi_core/report/results/0000_rms_norm_quant_reports/0000_rms_norm_quant.npu-rep) |
| 3_vf | 8,780 | 32 | 160 | 5 | [Open](NPUSim_Prof_Live_Demo/results/rms_norm_quant_3_vf/npusim_20261105120957_rms_norm_quant_3_vf/report/results/0000_rms_norm_quant_reports/0000_rms_norm_quant.npu-rep) |
| 4_double_buffer | 7,746 | 32 | 160 | 5 | [Open](NPUSim_Prof_Live_Demo/results/rms_norm_quant_4_double_buffer/npusim_20261105121219_rms_norm_quant_4_double_buffer/report/results/0000_rms_norm_quant_reports/0000_rms_norm_quant.npu-rep) |
| 5_ub_utilization | 7,720 | 32 | 64 | 2 | [Open](NPUSim_Prof_Live_Demo/results/rms_norm_quant_5_ub_utilization/npusim_20261105121436_rms_norm_quant_5_ub_utilization/report/results/0000_rms_norm_quant_reports/0000_rms_norm_quant.npu-rep) |
| 6_binary_sum | 7,759 | 32 | 96 | 3 | [Open](NPUSim_Prof_Live_Demo/results/rms_norm_quant_6_binary_sum/npusim_20261105121642_rms_norm_quant_6_binary_sum/report/results/0000_rms_norm_quant_reports/0000_rms_norm_quant.npu-rep) |

Kernel clocks measure simulated device execution in the collected report.
Host recording and analysis take minutes; do not interpret that elapsed time as
kernel latency. Exact paths, hashes and settings are in
[recording-manifest.json](NPUSim_Prof_Live_Demo/recording-manifest.json).

## Open the viewer before the presentation

Open the [web viewer](https://profiling-report.vercel.app/), select **en**, then
use **Open file…** to import the chosen `.npu-rep` above. The VS Code profiling
extension is another option; installation is described in README.

The main view is **Timeline**. Use the **AIV0** groups from core 0, collapse the
SCALAR slot rows, and expand MTE2, MTE3, PUSHQ, RVECLD and RVECST for comparison.
Selecting an instruction opens **Details → Parameter**. Match instruction names
and source call sites; a PC belongs to a particular binary and can change after
recompilation. Count `VF` on `AIV0_PUSHQ`, not producer events on PUSHQ_DISPATCH.

In **Report statistics**, click **Performance analysis** at the top right.
Messages appear in the bottom panel's **Hint Message** column. `HintPassed=1`
means the rule ran; it does not mean a message was emitted. Source-line fields
may be unspecified for kernel-level hints.

For memory coverage, expand **Memory load analysis → Memory topology**, choose
**UB**, and check the owner (AIV0 UB). The grid shows addresses touched by
recorded accesses; it does not measure live allocation or bandwidth saturation.
The viewer's other memory tabs do not imply those datasets were collected.

## 0 → 1: remove repeated gamma traffic

“Each input row changes, while gamma is shared. In the baseline `Process()`
loads both again inside the row loop. We move the gamma load and conversion
outside that loop. The recurring pair of MTE2 copies becomes one initial gamma
copy followed by row loads. Inspect the initial section and several steady-state
rows on the same core.”

The recorded AIV0 input transfers change from
**256 to 129**.
Kernel clocks change from **112,319 to 111,462**
(0.8% reduction).
Use the table below to compare stores and setup events as well; gamma preload
does not necessarily reduce the total number of VF calls.

Sources: [0_naive.asc](NPUSim_Prof_Live_Demo/cann-samples/Samples/2_Performance/rms_norm_quant_story/src/0_naive.asc) and
[1_preload_gamma.asc](NPUSim_Prof_Live_Demo/cann-samples/Samples/2_Performance/rms_norm_quant_story/src/1_preload_gamma.asc).

## 1 → 2: distribute rows across all vector cores

“Rows are independent, so version 2 distributes them across all 32 AIV lanes.
The full-core report confirms the launch with `ai_core_active=32` and 16 physical
core IDs, each containing AIV0 and AIV1. Inspect any lane to see its shorter
row sequence.”

Recorded output transfers change from
**128 to 4**,
and VF executions per AIV from **385 to 13**. Kernel clocks change
from **111,462 to 8,789** (12.68×).
Use the per-core trace for event counts and the summary for whole-kernel totals.

Source: [2_multi_core.asc](NPUSim_Prof_Live_Demo/cann-samples/Samples/2_Performance/rms_norm_quant_story/src/2_multi_core.asc).

## 2 → 5: combine vector work and batch rows in UB

“Version 2 has many separate row-level VF calls and DMA transfers. Version 5
keeps more computation together and batches the rows in UB. On the same recorded
context, VF executions per AIV fall from **13 to 2**. Expand PUSHQ, then compare
the recurring MTE2/MTE3 transfers and the vector load/store groups.”

Input-copy events change from **5
to 2**; output copies change from
**4 to 1**.
Kernel clocks fall from **8,789 to 7,720**
(12.2% reduction).
This comparison combines MicroAPI computation, buffering and batching; it does
not isolate the contribution of one change. Inspect 3 → 4 to study buffering.
Fewer DMA commands do not imply a smaller input/output payload.

Source: [5_ub_utilization.asc](NPUSim_Prof_Live_Demo/cann-samples/Samples/2_Performance/rms_norm_quant_story/src/5_ub_utilization.asc).

## Measured timeline reference: core 0 / AIV0

These counts come directly from the core-0 Chrome traces, deduplicated by
instruction ID within a lane group. One DMA instruction can appear on multiple
slot tracks, so visible boxes are not necessarily distinct instructions.
DMA counts use `MOV_SRC_TO_DST_ALIGNv2`, excluding `MOV_SPR_XN` setup. `RV_VST` is one mnemonic;
the RVECST lane also contains barriers and end markers.

| Lane / event | 0 | 1 | 2 | 5 |
| --- | ---: | ---: | ---: | ---: |
| AIV0_MTE2 / `MOV_SRC_TO_DST_ALIGNv2` | 256 | 129 | 5 | 2 |
| AIV0_MTE3 / `MOV_SRC_TO_DST_ALIGNv2` | 128 | 128 | 4 | 1 |
| AIV0_PUSHQ / `VF` | 384 | 385 | 13 | 2 |
| AIV0_PUSHQ / `PUSH_PB` | 640 | 513 | 17 | 4 |
| AIV0_RVECLD / `RV_VLD` | 2816 | 2308 | 76 | 56 |
| AIV0_RVECLD / `RV_VLDI` | 640 | 640 | 20 | 0 |
| AIV0_RVECST / `RV_VST` | 3328 | 2820 | 92 | 24 |
| AIV0_RVECST / `RV_SMEM_BAR` | 256 | 256 | 8 | 1 |
| AIV0_RVECST / `RV_SEND` | 384 | 385 | 13 | 2 |

Do not label arbitrary whitespace as a measured stall or infer that every
dependency disappeared. Check the actual overlap values and emitted hints in
each report. PMU/stall data availability is listed below; the old recordings'
absence of PMU data no longer describes this suite.

| Variant | VF PMU rows | SIMD sampling rows |
| --- | ---: | ---: |
| 0 | 215 | 4096 |
| 1 | 215 | 3972 |
| 2 | 215 | 3757 |
| 3 | 215 | 3584 |
| 4 | 215 | 3511 |
| 5 | 215 | 3715 |
| 6 | 215 | 3397 |

## Numerical checks and detectors

All seven output comparisons pass. Synchronization and race detectors answer
different questions, and their findings remain visible:

| Variant | Sync detector | Race detector |
| --- | --- | --- |
| 0 | [sync_instruction_detection] Found 3840 violation(s) — offending input lines: | [data_race_detection] No violations found. |
| 1 | [sync_instruction_detection] Found 2444 violation(s) — offending input lines: | [data_race_detection] No violations found. |
| 2 | [sync_instruction_detection] Found 2813 violation(s) — offending input lines: | [data_race_detection] No violations found. |
| 3 | [sync_instruction_detection] Found 3004 violation(s) — offending input lines: | [data_race_detection] No violations found. |
| 4 | [sync_instruction_detection] Found 3221 violation(s) — offending input lines: | [data_race_detection] No violations found. |
| 5 | [sync_instruction_detection] Found 852 violation(s) — offending input lines: | [data_race_detection] No violations found. |
| 6 | [sync_instruction_detection] Found 844 violation(s) — offending input lines: | [data_race_detection] No violations found. |

## Reproduce or regenerate

From the repository: `bash start.sh` builds and records all seven examples;
`bash start.sh 0 1 2 5` records the four presentation stops. From the extracted
package the same commands work. Python and NumPy are bundled; CANN and host
build tools must be installed. A physical NPU is unnecessary.

Single-core variants 0 and 1 have a one-hour timeout; the other variants default
to 15 minutes. `DEMO_TIMEOUT_SECONDS` overrides either limit. CPU affinity is
two slots; the RSS guard is 12 GiB with 1536 MiB of host memory kept available.

To regenerate report 5 from raw data without simulating again:

```bash
cd NPUSim_Prof_Live_Demo
source demo/env.sh
RUN="$DEMO_ROOT/results/rms_norm_quant_5_ub_utilization/npusim_20261105121436_rms_norm_quant_5_ub_utilization"
python3 -m npusim.main report -e "$RUN/record" -n all -o "$RUN/report-regenerated"
```

`CANNSIM_COLLECT=all` selects categories, not cores. `REPORT_CORES` defaults to
`0` for variants 0–1 and `all` for 2–6; `RMS_DEMO_CORES=32` is the build-time
launch cap for multi-core variants.

## Historical viewer screenshots

The PNGs in [figures/demo](figures/demo/) are captures of the previous October 28
CANN multi-core suite. They illustrate the UI only; their timings, instruction
PCs, counts and hint lists are not evidence for the new recordings. The old raw
profiles are excluded from the current archive. For the current values, import
the linked November 5 `.npu-rep` files and use the tables above.
