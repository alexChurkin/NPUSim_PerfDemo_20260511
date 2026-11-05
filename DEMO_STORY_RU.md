# От повторных передач к пакетным вычислениям — новый CANN

[English version](DEMO_STORY.md) · [Подготовка](README.md) · [Все результаты](NPUSim_Prof_Live_Demo/RESULTS.html)

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

| Variant | Kernel clocks | VF executions | .npu-rep |
| --- | ---: | ---: | --- |
| 0_naive | 112,319 | 384 | [Open](NPUSim_Prof_Live_Demo/results/rms_norm_quant_0_naive/npusim_20261105092401_rms_norm_quant_0_naive/report/results/0000_rms_norm_quant_reports/0000_rms_norm_quant.npu-rep) |
| 1_preload_gamma | 111,462 | 385 | [Open](NPUSim_Prof_Live_Demo/results/rms_norm_quant_1_preload_gamma/npusim_20261105094102_rms_norm_quant_1_preload_gamma/report/results/0000_rms_norm_quant_reports/0000_rms_norm_quant.npu-rep) |
| 2_multi_core | 57,607 | 193 | [Open](NPUSim_Prof_Live_Demo/results/rms_norm_quant_2_multi_core/npusim_20261105091038_rms_norm_quant_2_multi_core/report/results/0000_rms_norm_quant_reports/0000_rms_norm_quant.npu-rep) |
| 3_vf | 49,451 | 65 | [Open](NPUSim_Prof_Live_Demo/results/rms_norm_quant_3_vf/npusim_20261105095726_rms_norm_quant_3_vf/report/results/0000_rms_norm_quant_reports/0000_rms_norm_quant.npu-rep) |
| 4_double_buffer | 30,689 | 65 | [Open](NPUSim_Prof_Live_Demo/results/rms_norm_quant_4_double_buffer/npusim_20261105100524_rms_norm_quant_4_double_buffer/report/results/0000_rms_norm_quant_reports/0000_rms_norm_quant.npu-rep) |
| 5_ub_utilization | 13,033 | 2 | [Open](NPUSim_Prof_Live_Demo/results/rms_norm_quant_5_ub_utilization/npusim_20261105092000_rms_norm_quant_5_ub_utilization/report/results/0000_rms_norm_quant_reports/0000_rms_norm_quant.npu-rep) |
| 6_binary_sum | 13,099 | 3 | [Open](NPUSim_Prof_Live_Demo/results/rms_norm_quant_6_binary_sum/npusim_20261105101052_rms_norm_quant_6_binary_sum/report/results/0000_rms_norm_quant_reports/0000_rms_norm_quant.npu-rep) |

Такты — время выполнения в модели устройства для собранного отчёта.
Минуты записи и анализа на компьютере — другая величина. Точные пути, настройки
и SHA-256 отчётов есть в [манифесте](NPUSim_Prof_Live_Demo/recording-manifest.json).

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
**256 на 129**.
Такты: **112,319 → 111,462**,
снижение на **0.8%**.
По таблице ниже также сравниваем записи в UB и подготовку аргументов.
Предзагрузка gamma не обязана уменьшать общее число VF-вызовов.

Исходники: [0_naive.asc](NPUSim_Prof_Live_Demo/cann-samples/Samples/2_Performance/rms_norm_quant_story/src/0_naive.asc),
[1_preload_gamma.asc](NPUSim_Prof_Live_Demo/cann-samples/Samples/2_Performance/rms_norm_quant_story/src/1_preload_gamma.asc).

## 1 → 2: распределить строки и помнить об области сбора

«Строки независимы, поэтому вариант 2 распределяет их между двумя запускаемыми
векторными ядрами. В записанном контексте последовательность строк короче.
Изменение подтверждают исходный код и объём работы на контекст; отчёт только
по core 0 не позволяет подтвердить загрузку всего устройства».

Выходных копирований стало **64
вместо 128**,
VF-вызовов — **193 вместо 385**.
Такты в отчёте: **111,462 → 57,607** (1.93×).
Показываем оставшиеся сообщения о недостаточном параллелизме и объясняем
ограничение сбора вместо обещания, что эти сообщения исчезли.

Исходник: [2_multi_core.asc](NPUSim_Prof_Live_Demo/cann-samples/Samples/2_Performance/rms_norm_quant_story/src/2_multi_core.asc).

## 2 → 5: объединить векторные вычисления и обрабатывать строки пачкой

«В варианте 2 много отдельных VF-вызовов и передач для каждой строки.
В варианте 5 держим больше вычислений вместе и обрабатываем пачку строк в UB.
На том же контексте VF-вызовов становится **2 вместо 193**.
Раскрываем PUSHQ, затем сравниваем MTE2/MTE3 и группы векторных загрузок/записей».

Входные копирования: **65
→ 2**; выходные:
**64 → 1**.
Такты: **57,607 → 13,033**,
снижение на **77.4%**.
Здесь одновременно меняются MicroAPI-вычисления, буферизация и работа пачкой;
весь выигрыш нельзя приписать одному из этих изменений. Буферизацию отдельно
смотрим на 3 → 4. Меньше DMA-команд не означает меньший объём входа и выхода.

Исходник: [5_ub_utilization.asc](NPUSim_Prof_Live_Demo/cann-samples/Samples/2_Performance/rms_norm_quant_story/src/5_ub_utilization.asc).

## Справочная таблица таймлайна: core 0 / AIV0

Числа посчитаны по новым Chrome traces с удалением повторов по `instr_id`
внутри группы дорожек. Одна DMA-инструкция может отображаться на нескольких
слотах: в отчёте 5 три прямоугольника MTE2 соответствуют двум инструкциям копирования.
Для DMA считаем `MOV_SRC_TO_DST_ALIGNv2`, исключая подготовку `MOV_SPR_XN`. `RV_VST` — отдельная
инструкция, а дорожка RVECST также содержит барьеры и маркеры завершения VF.

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

Произвольный пустой участок не называем измеренным stall. Меньше событий не
доказывает исчезновение всех зависимостей. Проверяем значения перекрытия и
сообщения каждого отчёта. Наличие PMU и SIMD sampling в новых записях:

| Variant | VF PMU rows | SIMD sampling rows |
| --- | ---: | ---: |
| 0 | 215 | 4096 |
| 1 | 215 | 3972 |
| 2 | 215 | 1887 |
| 3 | 215 | 1792 |
| 4 | 215 | 1740 |
| 5 | 215 | 1856 |
| 6 | 215 | 1486 |

Прежнее описание об отсутствии PMU-данных к этой серии уже не относится.

## Проверка результата и детекторы

Все семь численных проверок пройдены. Детекторы синхронизации и гонок отвечают
на другие вопросы; их результаты сохранены:

| Variant | Sync detector | Race detector |
| --- | --- | --- |
| 0 | [sync_instruction_detection] Found 3840 violation(s) — offending input lines: | [data_race_detection] No violations found. |
| 1 | [sync_instruction_detection] Found 2444 violation(s) — offending input lines: | [data_race_detection] No violations found. |
| 2 | [sync_instruction_detection] Found 1232 violation(s) — offending input lines: | [data_race_detection] No violations found. |
| 3 | [sync_instruction_detection] Found 1518 violation(s) — offending input lines: | [data_race_detection] No violations found. |
| 4 | [sync_instruction_detection] Found 1446 violation(s) — offending input lines: | [data_race_detection] No violations found. |
| 5 | [sync_instruction_detection] Found 34 violation(s) — offending input lines: | [data_race_detection] No violations found. |
| 6 | [sync_instruction_detection] Found 27 violation(s) — offending input lines: | [data_race_detection] No violations found. |

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
RUN="$DEMO_ROOT/results/rms_norm_quant_5_ub_utilization/npusim_20261105092000_rms_norm_quant_5_ub_utilization"
python3 -m npusim.main report -e "$RUN/record" -n 0 -o "$RUN/report-regenerated"
```

`CANNSIM_COLLECT=all` выбирает категории, а не ядра.
`REPORT_CORES=0` задаёт сбор, `RMS_DEMO_CORES=2` — предел запуска при сборке.

## Исторические скриншоты просмотрщика

PNG в [figures/demo](figures/demo/) сняты с прежней серии на CANN от 28 октября
с записью 32 ядер. Они иллюстрируют интерфейс; их такты, PC, счётчики и списки
хинтов не подтверждают значения новой серии. Старые записи исключены из нового
архива. Для текущих значений открываем `.npu-rep` от 5 ноября из таблицы выше.
