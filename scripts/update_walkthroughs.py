#!/usr/bin/env python3
"""Write bilingual presenter notes from the seven verified current recordings."""
import gzip
import json
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ROOT = REPO / 'NPUSim_Prof_Live_Demo'


def event_counts(item):
    path = ROOT / item['artifacts']['traces'][0]
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt') as stream:
        events = json.load(stream)['traceEvents']
    lanes = {e['pid']: e['args']['name'].split(' ')[0] for e in events
             if e.get('ph') == 'M' and e.get('name') == 'process_name'}
    counts = Counter()
    seen = set()
    for event in events:
        if event.get('ph') != 'X':
            continue
        instruction = event.get('args', {}).get('instr_id')
        if instruction is None:
            instruction = (event['ts'], event.get('dur'), event.get('args', {}).get('pc'))
        key = (event.get('pid'), event.get('name'), instruction)
        if key in seen:
            continue
        seen.add(key)
        counts[lanes.get(event.get('pid')), event.get('name')] += 1
    return counts


def main():
    items = json.loads((ROOT / 'latest-measurements.json').read_text())
    by_stage = {int(i['variant'].split('_')[3]): i for i in items}
    assert set(by_stage) == set(range(7))
    assert all(Path(i['run']).name.startswith('npusim_20261105') and i['precision_ok'] for i in items)
    metrics = {s: i['summaries'][0]['data'] for s, i in by_stage.items()}
    counts = {s: event_counts(i) for s, i in by_stage.items()}
    clocks = {s: m['kernel_info']['kernel_total_clocks'] for s, m in metrics.items()}
    vf = {s: m['simd_vf_metrics']['vf_total_executions'] for s, m in metrics.items()}
    vf_per = {s: m['simd_vf_metrics']['vf_executions_per_core'] for s, m in metrics.items()}
    active = {s: m['kernel_info']['ai_core_active'] for s, m in metrics.items()}
    source = 'cann-samples/Samples/2_Performance/rms_norm_quant_story/src/'
    patterns = [('AIV0_MTE2', 'MOV_SRC_TO_DST_ALIGNv2'),
                ('AIV0_MTE3', 'MOV_SRC_TO_DST_ALIGNv2'), ('AIV0_PUSHQ', 'VF'),
                ('AIV0_PUSHQ', 'PUSH_PB'), ('AIV0_RVECLD', 'RV_VLD'),
                ('AIV0_RVECLD', 'RV_VLDI'), ('AIV0_RVECST', 'RV_VST'),
                ('AIV0_RVECST', 'RV_SMEM_BAR'), ('AIV0_RVECST', 'RV_SEND')]
    lane_table = '| Lane / event | 0 | 1 | 2 | 5 |\n| --- | ---: | ---: | ---: | ---: |\n'
    for lane, event in patterns:
        lane_table += f'| {lane} / `{event}` | ' + ' | '.join(str(counts[s][lane, event]) for s in (0, 1, 2, 5)) + ' |\n'
    for base, prefix in ((REPO, 'NPUSim_Prof_Live_Demo/'), (ROOT, '')):
        table = '| Variant | Kernel clocks | Active AIV | VF total | VF / AIV | .npu-rep |\n| --- | ---: | ---: | ---: | ---: | --- |\n'
        for s in range(7):
            i = by_stage[s]
            table += f"| {i['variant'].removeprefix('rms_norm_quant_')} | {clocks[s]:,} | {active[s]} | {vf[s]:,} | {vf_per[s]:g} | [Open]({prefix + i['artifacts']['archives'][0]}) |\n"
        diagnostics = '| Variant | Sync detector | Race detector |\n| --- | --- | --- |\n'
        for s in range(7):
            d = by_stage[s].get('detections', {})
            diagnostics += f"| {s} | {d.get('sync_instruction_detection', 'not recorded')} | {d.get('data_race_detection', 'not recorded')} |\n"
        pmu = '| Variant | VF PMU rows | SIMD sampling rows |\n| --- | ---: | ---: |\n'
        for s in range(7):
            rows = by_stage[s].get('collection_rows', {})
            pmu += f"| {s} | {rows.get('VfPMUMetrics', 0)} | {rows.get('SIMDSamplingStats', 0)} |\n"
        en = f'''# From repeated traffic to batched computation — new CANN recordings

[Русская версия](DEMO_STORY_RU.md) · [Setup](README.md) · [Offline results]({prefix}RESULTS.html)

**Four stops, 7–9 minutes: 0 → 1 → 2 → 5.** These reports were recorded on
November 5, 2026 with CANN **9.3.0 / V100R001C13B046**, build **20261104000324968**.
The shape is **128 × 256**, the target is Ascend950/dav-3510, and all seven
numerical checks pass with absolute int8 tolerance 1.

Variants 0 and 1 intentionally launch and record one vector core. Variants 2–6
launch all **32 AIV lanes** and record with `--core-id all`. The database has
16 physical core IDs, each with AIV0 and AIV1; the report has 16 per-core trace
files and `ai_core_active=32`. The VF totals below span all active AIV lanes;
the timeline event table further down is explicitly for core 0 / AIV0.

{table}
Kernel clocks measure simulated device execution in the collected report.
Host recording and analysis take minutes; do not interpret that elapsed time as
kernel latency. Exact paths, hashes and settings are in
[recording-manifest.json]({prefix}recording-manifest.json).

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
**{counts[0]['AIV0_MTE2', 'MOV_SRC_TO_DST_ALIGNv2']} to {counts[1]['AIV0_MTE2', 'MOV_SRC_TO_DST_ALIGNv2']}**.
Kernel clocks change from **{clocks[0]:,} to {clocks[1]:,}**
({(1 - clocks[1] / clocks[0]) * 100:.1f}% reduction).
Use the table below to compare stores and setup events as well; gamma preload
does not necessarily reduce the total number of VF calls.

Sources: [0_naive.asc]({prefix + source}0_naive.asc) and
[1_preload_gamma.asc]({prefix + source}1_preload_gamma.asc).

## 1 → 2: distribute rows across all vector cores

“Rows are independent, so version 2 distributes them across all 32 AIV lanes.
The full-core report confirms the launch with `ai_core_active=32` and 16 physical
core IDs, each containing AIV0 and AIV1. Inspect any lane to see its shorter
row sequence.”

Recorded output transfers change from
**{counts[1]['AIV0_MTE3', 'MOV_SRC_TO_DST_ALIGNv2']} to {counts[2]['AIV0_MTE3', 'MOV_SRC_TO_DST_ALIGNv2']}**,
and VF executions per AIV from **{vf_per[1]:g} to {vf_per[2]:g}**. Kernel clocks change
from **{clocks[1]:,} to {clocks[2]:,}** ({clocks[1] / clocks[2]:.2f}×).
Use the per-core trace for event counts and the summary for whole-kernel totals.

Source: [2_multi_core.asc]({prefix + source}2_multi_core.asc).

## 2 → 5: combine vector work and batch rows in UB

“Version 2 has many separate row-level VF calls and DMA transfers. Version 5
keeps more computation together and batches the rows in UB. On the same recorded
context, VF executions per AIV fall from **{vf_per[2]:g} to {vf_per[5]:g}**. Expand PUSHQ, then compare
the recurring MTE2/MTE3 transfers and the vector load/store groups.”

Input-copy events change from **{counts[2]['AIV0_MTE2', 'MOV_SRC_TO_DST_ALIGNv2']}
to {counts[5]['AIV0_MTE2', 'MOV_SRC_TO_DST_ALIGNv2']}**; output copies change from
**{counts[2]['AIV0_MTE3', 'MOV_SRC_TO_DST_ALIGNv2']} to {counts[5]['AIV0_MTE3', 'MOV_SRC_TO_DST_ALIGNv2']}**.
Kernel clocks fall from **{clocks[2]:,} to {clocks[5]:,}**
({(1 - clocks[5] / clocks[2]) * 100:.1f}% reduction).
This comparison combines MicroAPI computation, buffering and batching; it does
not isolate the contribution of one change. Inspect 3 → 4 to study buffering.
Fewer DMA commands do not imply a smaller input/output payload.

Source: [5_ub_utilization.asc]({prefix + source}5_ub_utilization.asc).

## Measured timeline reference: core 0 / AIV0

These counts come directly from the core-0 Chrome traces, deduplicated by
instruction ID within a lane group. One DMA instruction can appear on multiple
slot tracks, so visible boxes are not necessarily distinct instructions.
DMA counts use `MOV_SRC_TO_DST_ALIGNv2`, excluding `MOV_SPR_XN` setup. `RV_VST` is one mnemonic;
the RVECST lane also contains barriers and end markers.

{lane_table}
Do not label arbitrary whitespace as a measured stall or infer that every
dependency disappeared. Check the actual overlap values and emitted hints in
each report. PMU/stall data availability is listed below; the old recordings'
absence of PMU data no longer describes this suite.

{pmu}
## Numerical checks and detectors

All seven output comparisons pass. Synchronization and race detectors answer
different questions, and their findings remain visible:

{diagnostics}
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
RUN="$DEMO_ROOT/{by_stage[5]['run']}"
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
'''
        ru = f'''# От повторных передач к пакетным вычислениям — новый CANN

[English version](DEMO_STORY.md) · [Подготовка](README.md) · [Все результаты]({prefix}RESULTS.html)

**Четыре остановки, 7–9 минут: 0 → 1 → 2 → 5.** Отчёты записаны
5 ноября 2026 на CANN **9.3.0 / V100R001C13B046**, сборка **20261104000324968**.
Форма — **128 × 256**, цель — Ascend950/dav-3510. Все семь численных проверок
пройдены с исходным допуском: абсолютная разница int8 не больше 1.

Варианты 0 и 1 намеренно запускают и записывают одно векторное ядро.
Варианты 2–6 запускают все **32 дорожки AIV** и записываются с `--core-id all`.
В базе 16 физических core ID, у каждого есть AIV0 и AIV1; в отчёте 16 трасс,
а `ai_core_active=32`. Суммы VF ниже относятся ко всем активным AIV;
таблица событий таймлайна ниже относится только к core 0 / AIV0.

{table}
Такты — время выполнения в модели устройства для собранного отчёта.
Минуты записи и анализа на компьютере — другая величина. Точные пути, настройки
и SHA-256 отчётов есть в [манифесте]({prefix}recording-manifest.json).

## Перед выступлением: открыть просмотрщик

Открываем [веб-просмотрщик](https://profiling-report.vercel.app/), выбираем **en**
и через **Open file…** импортируем `.npu-rep` из таблицы. Можно использовать
расширение VS Code; установка описана в README.

На **Timeline** используем группы **AIV0** для core 0. Сворачиваем SCALAR slot,
раскрываем MTE2, MTE3, PUSHQ, RVECLD и RVECST. Выбор инструкции открывает
**Details → Parameter**. Сопоставляем имена инструкций и места вызова в исходнике;
PC относится к конкретному бинарнику и после пересборки может измениться.
Считаем `VF` на `AIV0_PUSHQ`, а не события производителя на PUSHQ_DISPATCH.

В правой панели **Report statistics** нажимаем **Performance analysis** сверху
справа. Сообщения появляются в нижней панели, в столбце **Hint Message**.
`HintPassed=1` означает, что правило выполнилось; это не означает наличие
сообщения. Привязка хинта уровня ядра к строке исходника может отсутствовать.

Для памяти открываем **Memory load analysis → Memory topology → UB** и
проверяем владельца карты — AIV0 UB. Сетка показывает затронутые адреса;
она не измеряет живые выделения тензоров или насыщение пропускной способности.
Наличие других вкладок памяти в интерфейсе не подтверждает наличие их данных.

## 0 → 1: убрать повторную загрузку gamma

«Входная строка каждый раз новая, а gamma общая. В исходном `Process()` обе
загружаются внутри цикла. Выносим загрузку и преобразование gamma перед циклом.
Повторяющиеся пары копирований на MTE2 превращаются в одну начальную загрузку
gamma и дальнейшие загрузки строк. Смотрим начало и несколько строк основного
цикла на том же ядре».

В записанном AIV0 число входных копирований меняется с
**{counts[0]['AIV0_MTE2', 'MOV_SRC_TO_DST_ALIGNv2']} на {counts[1]['AIV0_MTE2', 'MOV_SRC_TO_DST_ALIGNv2']}**.
Такты: **{clocks[0]:,} → {clocks[1]:,}**,
снижение на **{(1 - clocks[1] / clocks[0]) * 100:.1f}%**.
По таблице ниже также сравниваем записи в UB и подготовку аргументов.
Предзагрузка gamma не обязана уменьшать общее число VF-вызовов.

Исходники: [0_naive.asc]({prefix + source}0_naive.asc),
[1_preload_gamma.asc]({prefix + source}1_preload_gamma.asc).

## 1 → 2: распределить строки по всем векторным ядрам

«Строки независимы, поэтому вариант 2 распределяет их по всем 32 дорожкам AIV.
Полный отчёт подтверждает запуск: `ai_core_active=32` и 16 физических core ID,
каждый с AIV0 и AIV1. На любой дорожке видно более короткую последовательность
строк».

Выходных копирований стало **{counts[2]['AIV0_MTE3', 'MOV_SRC_TO_DST_ALIGNv2']}
вместо {counts[1]['AIV0_MTE3', 'MOV_SRC_TO_DST_ALIGNv2']}**,
VF-вызовов на AIV — **{vf_per[2]:g} вместо {vf_per[1]:g}**.
Такты: **{clocks[1]:,} → {clocks[2]:,}** ({clocks[1] / clocks[2]:.2f}×).
Число событий смотрим по конкретной трассе, а сумму по всем ядрам — в сводке.

Исходник: [2_multi_core.asc]({prefix + source}2_multi_core.asc).

## 2 → 5: объединить векторные вычисления и обрабатывать строки пачкой

«В варианте 2 много отдельных VF-вызовов и передач для каждой строки.
В варианте 5 держим больше вычислений вместе и обрабатываем пачку строк в UB.
На том же контексте VF-вызовов на AIV становится **{vf_per[5]:g} вместо {vf_per[2]:g}**.
Раскрываем PUSHQ, затем сравниваем MTE2/MTE3 и группы векторных загрузок/записей».

Входные копирования: **{counts[2]['AIV0_MTE2', 'MOV_SRC_TO_DST_ALIGNv2']}
→ {counts[5]['AIV0_MTE2', 'MOV_SRC_TO_DST_ALIGNv2']}**; выходные:
**{counts[2]['AIV0_MTE3', 'MOV_SRC_TO_DST_ALIGNv2']} → {counts[5]['AIV0_MTE3', 'MOV_SRC_TO_DST_ALIGNv2']}**.
Такты: **{clocks[2]:,} → {clocks[5]:,}**,
снижение на **{(1 - clocks[5] / clocks[2]) * 100:.1f}%**.
Здесь одновременно меняются MicroAPI-вычисления, буферизация и работа пачкой;
весь выигрыш нельзя приписать одному из этих изменений. Буферизацию отдельно
смотрим на 3 → 4. Меньше DMA-команд не означает меньший объём входа и выхода.

Исходник: [5_ub_utilization.asc]({prefix + source}5_ub_utilization.asc).

## Справочная таблица таймлайна: core 0 / AIV0

Числа посчитаны по Chrome traces для core 0 с удалением повторов по `instr_id`
внутри группы дорожек. Одна DMA-инструкция может отображаться на нескольких
слотах, поэтому число прямоугольников не обязательно равно числу инструкций.
Для DMA считаем `MOV_SRC_TO_DST_ALIGNv2`, исключая подготовку `MOV_SPR_XN`. `RV_VST` — отдельная
инструкция, а дорожка RVECST также содержит барьеры и маркеры завершения VF.

{lane_table}
Произвольный пустой участок не называем измеренным stall. Меньше событий не
доказывает исчезновение всех зависимостей. Проверяем значения перекрытия и
сообщения каждого отчёта. Наличие PMU и SIMD sampling в новых записях:

{pmu}
Прежнее описание об отсутствии PMU-данных к этой серии уже не относится.

## Проверка результата и детекторы

Все семь численных проверок пройдены. Детекторы синхронизации и гонок отвечают
на другие вопросы; их результаты сохранены:

{diagnostics}
## Повторный запуск

Из корня репозитория `bash start.sh` собирает и записывает все семь вариантов;
`bash start.sh 0 1 2 5` — четыре остановки сценария. Из распакованной демки
работают те же команды. Python и NumPy включены в пакет; CANN и инструменты
сборки должны быть установлены. Физический NPU не требуется.

Для однокорных 0 и 1 таймаут — час; для остальных — 15 минут.
`DEMO_TIMEOUT_SECONDS` переопределяет это значение. Affinity — два CPU,
RSS ограничен 12 ГиБ, резерв доступной памяти — 1536 МиБ.

Пересоздать отчёт 5 из записи без повторного расчёта:

```bash
cd NPUSim_Prof_Live_Demo
source demo/env.sh
RUN="$DEMO_ROOT/{by_stage[5]['run']}"
python3 -m npusim.main report -e "$RUN/record" -n all -o "$RUN/report-regenerated"
```

`CANNSIM_COLLECT=all` выбирает категории, а не ядра.
`REPORT_CORES` по умолчанию равен `0` для вариантов 0–1 и `all` для 2–6;
`RMS_DEMO_CORES=32` задаёт предел запуска при сборке многокорных вариантов.

## Исторические скриншоты просмотрщика

PNG в [figures/demo](figures/demo/) сняты с прежней серии на CANN от 28 октября
с многокорной записью. Они иллюстрируют интерфейс; их такты, PC, счётчики и списки
хинтов не подтверждают значения новой серии. Старые записи исключены из нового
архива. Для текущих значений открываем `.npu-rep` от 5 ноября из таблицы выше.
'''
        (base / 'DEMO_STORY.md').write_text(en)
        (base / 'DEMO_STORY_RU.md').write_text(ru)
    print('Updated both walkthroughs in the repository and extracted package')


if __name__ == '__main__':
    main()
