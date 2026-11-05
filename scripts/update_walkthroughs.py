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
        table = '| Variant | Kernel clocks | VF executions | .npu-rep |\n| --- | ---: | ---: | --- |\n'
        for s in range(7):
            i = by_stage[s]
            table += f"| {i['variant'].removeprefix('rms_norm_quant_')} | {clocks[s]:,} | {vf[s]:,} | [Open]({prefix + i['artifacts']['archives'][0]}) |\n"
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

Variants 0 and 1 launch one vector core; variants 2–6 use a launch cap of two.
Reports collect **core 0 only**. All counts and clocks below describe that
recorded subset, not the combined work across the chip. In particular,
`ai_core_active=1` and Small Grid / Single-core hints in a filtered report do
not prove that the launcher used only one core. Do not reuse the old claim that
these hints disappear in report 2 or that all 32 physical cores were recorded.

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

## 1 → 2: distribute rows, while keeping the collection scope clear

“Rows are independent, so version 2 distributes them across the two launched
vector cores. On the recorded context the long row sequence is shorter.
This demonstrates the launch change through the source and per-context work,
while the single-core report cannot certify utilization of the full device.”

Recorded output transfers change from
**{counts[1]['AIV0_MTE3', 'MOV_SRC_TO_DST_ALIGNv2']} to {counts[2]['AIV0_MTE3', 'MOV_SRC_TO_DST_ALIGNv2']}**,
and VF executions from **{vf[1]} to {vf[2]}**. Collected kernel clocks change
from **{clocks[1]:,} to {clocks[2]:,}** ({clocks[1] / clocks[2]:.2f}×).
Keep the under-launch messages visible and explain the core-0 collection scope
instead of promising that they vanish.

Source: [2_multi_core.asc]({prefix + source}2_multi_core.asc).

## 2 → 5: combine vector work and batch rows in UB

“Version 2 has many separate row-level VF calls and DMA transfers. Version 5
keeps more computation together and batches the rows in UB. On the same recorded
context, VF executions fall from **{vf[2]} to {vf[5]}**. Expand PUSHQ, then compare
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

These counts come directly from the new Chrome traces, deduplicated by
instruction ID within a lane group. One DMA instruction can appear on multiple
slot tracks: report 5 shows three MTE2 boxes but only two distinct copy instructions.
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
'''
        ru = f'''# От повторных передач к пакетным вычислениям — новый CANN

[English version](DEMO_STORY.md) · [Подготовка](README.md) · [Все результаты]({prefix}RESULTS.html)

**Четыре остановки, 7–9 минут: 0 → 1 → 2 → 5.** Отчёты записаны
5 ноября 2026 на CANN **9.3.0 / V100R001C13B046**, сборка **20261104000324968**.
Форма — **128 × 256**, цель — Ascend950/dav-3510. Все семь численных проверок
пройдены с исходным допуском: абсолютная разница int8 не больше 1.

Варианты 0 и 1 запускают одно векторное ядро; для 2–6 предел запуска — два.
В отчёт собирается **только core 0**. Все числа ниже относятся к собранной
части выполнения, а не к сумме по всему чипу. `ai_core_active=1` и сообщения
Small Grid / Single-core в таком отчёте не доказывают запуск только одного ядра.
Прежние утверждения об исчезновении этих хинтов в варианте 2 и о записи всех
32 физических ядер к новой серии неприменимы.

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

## 1 → 2: распределить строки и помнить об области сбора

«Строки независимы, поэтому вариант 2 распределяет их между двумя запускаемыми
векторными ядрами. В записанном контексте последовательность строк короче.
Изменение подтверждают исходный код и объём работы на контекст; отчёт только
по core 0 не позволяет подтвердить загрузку всего устройства».

Выходных копирований стало **{counts[2]['AIV0_MTE3', 'MOV_SRC_TO_DST_ALIGNv2']}
вместо {counts[1]['AIV0_MTE3', 'MOV_SRC_TO_DST_ALIGNv2']}**,
VF-вызовов — **{vf[2]} вместо {vf[1]}**.
Такты в отчёте: **{clocks[1]:,} → {clocks[2]:,}** ({clocks[1] / clocks[2]:.2f}×).
Показываем оставшиеся сообщения о недостаточном параллелизме и объясняем
ограничение сбора вместо обещания, что эти сообщения исчезли.

Исходник: [2_multi_core.asc]({prefix + source}2_multi_core.asc).

## 2 → 5: объединить векторные вычисления и обрабатывать строки пачкой

«В варианте 2 много отдельных VF-вызовов и передач для каждой строки.
В варианте 5 держим больше вычислений вместе и обрабатываем пачку строк в UB.
На том же контексте VF-вызовов становится **{vf[5]} вместо {vf[2]}**.
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

Числа посчитаны по новым Chrome traces с удалением повторов по `instr_id`
внутри группы дорожек. Одна DMA-инструкция может отображаться на нескольких
слотах: в отчёте 5 три прямоугольника MTE2 соответствуют двум инструкциям копирования.
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
python3 -m npusim.main report -e "$RUN/record" -n 0 -o "$RUN/report-regenerated"
```

`CANNSIM_COLLECT=all` выбирает категории, а не ядра.
`REPORT_CORES=0` задаёт сбор, `RMS_DEMO_CORES=2` — предел запуска при сборке.

## Исторические скриншоты просмотрщика

PNG в [figures/demo](figures/demo/) сняты с прежней серии на CANN от 28 октября
с записью 32 ядер. Они иллюстрируют интерфейс; их такты, PC, счётчики и списки
хинтов не подтверждают значения новой серии. Старые записи исключены из нового
архива. Для текущих значений открываем `.npu-rep` от 5 ноября из таблицы выше.
'''
        (base / 'DEMO_STORY.md').write_text(en)
        (base / 'DEMO_STORY_RU.md').write_text(ru)
    print('Updated both walkthroughs in the repository and extracted package')


if __name__ == '__main__':
    main()
