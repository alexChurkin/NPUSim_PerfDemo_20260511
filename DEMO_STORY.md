# From repeated traffic to batched computation — new CANN recordings

[Русская версия](DEMO_STORY_RU.md) · [Setup](README.md) · [Offline results](NPUSim_Prof_Live_Demo/RESULTS.html)

**Four stops, 7–9 minutes: 0 → 1 → 2 → 5.** These reports were recorded on
November 5, 2026 with CANN **9.3.0 / V100R001C13B046**, build **20261104000324968**.
The shape is **128 × 256**, the target is Ascend950/dav-3510, and all seven
numerical checks pass with absolute int8 tolerance 1.

Variants 0 and 1 launch one vector core; variants 2–6 use a launch cap of two.
Reports collect **core 0 only**. All counts and clocks below describe that
recorded subset, not the combined work across the chip. In particular,
`ai_core_active=1` and Small Grid / Single-core hints in a filtered report do
not prove that the launcher used only one core. Do not reuse the old claim that
these hints disappear in report 2 or that all 32 physical cores were recorded.

| Variant | Kernel clocks | VF executions | .npu-rep |
| --- | ---: | ---: | --- |
| 0_naive | 112,319 | 384 | [Open](NPUSim_Prof_Live_Demo/results/rms_norm_quant_0_naive/npusim_20261105092401_rms_norm_quant_0_naive/report/results/0000_rms_norm_quant_reports/0000_rms_norm_quant.npu-rep) |
| 1_preload_gamma | 111,462 | 385 | [Open](NPUSim_Prof_Live_Demo/results/rms_norm_quant_1_preload_gamma/npusim_20261105094102_rms_norm_quant_1_preload_gamma/report/results/0000_rms_norm_quant_reports/0000_rms_norm_quant.npu-rep) |
| 2_multi_core | 57,607 | 193 | [Open](NPUSim_Prof_Live_Demo/results/rms_norm_quant_2_multi_core/npusim_20261105091038_rms_norm_quant_2_multi_core/report/results/0000_rms_norm_quant_reports/0000_rms_norm_quant.npu-rep) |
| 3_vf | 49,451 | 65 | [Open](NPUSim_Prof_Live_Demo/results/rms_norm_quant_3_vf/npusim_20261105095726_rms_norm_quant_3_vf/report/results/0000_rms_norm_quant_reports/0000_rms_norm_quant.npu-rep) |
| 4_double_buffer | 30,689 | 65 | [Open](NPUSim_Prof_Live_Demo/results/rms_norm_quant_4_double_buffer/npusim_20261105100524_rms_norm_quant_4_double_buffer/report/results/0000_rms_norm_quant_reports/0000_rms_norm_quant.npu-rep) |
| 5_ub_utilization | 13,033 | 2 | [Open](NPUSim_Prof_Live_Demo/results/rms_norm_quant_5_ub_utilization/npusim_20261105092000_rms_norm_quant_5_ub_utilization/report/results/0000_rms_norm_quant_reports/0000_rms_norm_quant.npu-rep) |
| 6_binary_sum | 13,099 | 3 | [Open](NPUSim_Prof_Live_Demo/results/rms_norm_quant_6_binary_sum/npusim_20261105101052_rms_norm_quant_6_binary_sum/report/results/0000_rms_norm_quant_reports/0000_rms_norm_quant.npu-rep) |

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

## 1 → 2: distribute rows, while keeping the collection scope clear

“Rows are independent, so version 2 distributes them across the two launched
vector cores. On the recorded context the long row sequence is shorter.
This demonstrates the launch change through the source and per-context work,
while the single-core report cannot certify utilization of the full device.”

Recorded output transfers change from
**128 to 64**,
and VF executions from **385 to 193**. Collected kernel clocks change
from **111,462 to 57,607** (1.93×).
Keep the under-launch messages visible and explain the core-0 collection scope
instead of promising that they vanish.

Source: [2_multi_core.asc](NPUSim_Prof_Live_Demo/cann-samples/Samples/2_Performance/rms_norm_quant_story/src/2_multi_core.asc).

## 2 → 5: combine vector work and batch rows in UB

“Version 2 has many separate row-level VF calls and DMA transfers. Version 5
keeps more computation together and batches the rows in UB. On the same recorded
context, VF executions fall from **193 to 2**. Expand PUSHQ, then compare
the recurring MTE2/MTE3 transfers and the vector load/store groups.”

Input-copy events change from **65
to 2**; output copies change from
**64 to 1**.
Kernel clocks fall from **57,607 to 13,033**
(77.4% reduction).
This comparison combines MicroAPI computation, buffering and batching; it does
not isolate the contribution of one change. Inspect 3 → 4 to study buffering.
Fewer DMA commands do not imply a smaller input/output payload.

Source: [5_ub_utilization.asc](NPUSim_Prof_Live_Demo/cann-samples/Samples/2_Performance/rms_norm_quant_story/src/5_ub_utilization.asc).

## Measured timeline reference: core 0 / AIV0

These counts come directly from the new Chrome traces, deduplicated by
instruction ID within a lane group. One DMA instruction can appear on multiple
slot tracks: report 5 shows three MTE2 boxes but only two distinct copy instructions.
DMA counts use `MOV_SRC_TO_DST_ALIGNv2`, excluding `MOV_SPR_XN` setup. `RV_VST` is one mnemonic;
the RVECST lane also contains barriers and end markers.

| Lane / event | 0 | 1 | 2 | 5 |
| --- | ---: | ---: | ---: | ---: |
| AIV0_MTE2 / `MOV_SRC_TO_DST_ALIGNv2` | 256 | 129 | 65 | 2 |
| AIV0_MTE3 / `MOV_SRC_TO_DST_ALIGNv2` | 128 | 128 | 64 | 1 |
| AIV0_PUSHQ / `VF` | 384 | 385 | 193 | 2 |
| AIV0_PUSHQ / `PUSH_PB` | 640 | 513 | 257 | 4 |
| AIV0_RVECLD / `RV_VLD` | 2816 | 2308 | 1156 | 836 |
| AIV0_RVECLD / `RV_VLDI` | 640 | 640 | 320 | 0 |
| AIV0_RVECST / `RV_VST` | 3328 | 2820 | 1412 | 324 |
| AIV0_RVECST / `RV_SMEM_BAR` | 256 | 256 | 128 | 1 |
| AIV0_RVECST / `RV_SEND` | 384 | 385 | 193 | 2 |

Do not label arbitrary whitespace as a measured stall or infer that every
dependency disappeared. Check the actual overlap values and emitted hints in
each report. PMU/stall data availability is listed below; the old recordings'
absence of PMU data no longer describes this suite.

| Variant | VF PMU rows | SIMD sampling rows |
| --- | ---: | ---: |
| 0 | 215 | 4096 |
| 1 | 215 | 3972 |
| 2 | 215 | 1887 |
| 3 | 215 | 1792 |
| 4 | 215 | 1740 |
| 5 | 215 | 1856 |
| 6 | 215 | 1486 |

## Numerical checks and detectors

All seven output comparisons pass. Synchronization and race detectors answer
different questions, and their findings remain visible:

| Variant | Sync detector | Race detector |
| --- | --- | --- |
| 0 | [sync_instruction_detection] Found 3840 violation(s) — offending input lines: | [data_race_detection] No violations found. |
| 1 | [sync_instruction_detection] Found 2444 violation(s) — offending input lines: | [data_race_detection] No violations found. |
| 2 | [sync_instruction_detection] Found 1232 violation(s) — offending input lines: | [data_race_detection] No violations found. |
| 3 | [sync_instruction_detection] Found 1518 violation(s) — offending input lines: | [data_race_detection] No violations found. |
| 4 | [sync_instruction_detection] Found 1446 violation(s) — offending input lines: | [data_race_detection] No violations found. |
| 5 | [sync_instruction_detection] Found 34 violation(s) — offending input lines: | [data_race_detection] No violations found. |
| 6 | [sync_instruction_detection] Found 27 violation(s) — offending input lines: | [data_race_detection] No violations found. |

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
RUN="$DEMO_ROOT/results/rms_norm_quant_5_ub_utilization/npusim_20261105092000_rms_norm_quant_5_ub_utilization"
python3 -m npusim.main report -e "$RUN/record" -n 0 -o "$RUN/report-regenerated"
```

`CANNSIM_COLLECT=all` selects categories, not cores. Default `REPORT_CORES=0`
controls collection; `RMS_DEMO_CORES=2` controls the launch cap at build time.

## Historical viewer screenshots

The PNGs in [figures/demo](figures/demo/) are captures of the previous October 28
CANN / 32-core suite. They illustrate the UI only; their timings, instruction
PCs, counts and hint lists are not evidence for the new recordings. The old raw
profiles are excluded from the current archive. For the current values, import
the linked November 5 `.npu-rep` files and use the tables above.
