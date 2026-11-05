# От повторных передач к пакетным вычислениям — новый CANN

[English version](DEMO_STORY.md) · [Подготовка](README.md) · [Все результаты](NPUSim_Prof_Live_Demo/RESULTS.html)

**Четыре остановки, 7–9 минут: 0 → 1 → 2 → 5.** Отчёты записаны
5 ноября 2026 на CANN **9.3.0 / V100R001C13B046**, сборка **20261104000324968**.
Форма — **128 × 256**, цель — Ascend950/dav-3510. Все семь численных проверок
пройдены с исходным допуском: абсолютная разница int8 не больше 1.

Варианты 0 и 1 намеренно запускают и записывают одно векторное ядро.
Варианты 2–6 запускают все **32 дорожки AIV** и записываются с `--core-id all`.
В базе 16 физических core ID, у каждого есть AIV0 и AIV1; в отчёте 16 трасс,
а `ai_core_active=32`. Суммы VF ниже относятся ко всем активным AIV;
таблица событий таймлайна ниже относится только к core 0 / AIV0.

| Variant | Kernel clocks | Active AIV | VF total | VF / AIV | .npu-rep |
| --- | ---: | ---: | ---: | ---: | --- |
| 0_naive | 112,319 | 1 | 384 | 384 | [Open](NPUSim_Prof_Live_Demo/results/rms_norm_quant_0_naive/npusim_20261105092401_rms_norm_quant_0_naive/report/results/0000_rms_norm_quant_reports/0000_rms_norm_quant.npu-rep) |
| 1_preload_gamma | 111,462 | 1 | 385 | 385 | [Open](NPUSim_Prof_Live_Demo/results/rms_norm_quant_1_preload_gamma/npusim_20261105094102_rms_norm_quant_1_preload_gamma/report/results/0000_rms_norm_quant_reports/0000_rms_norm_quant.npu-rep) |
| 2_multi_core | 8,789 | 32 | 416 | 13 | [Open](NPUSim_Prof_Live_Demo/results/rms_norm_quant_2_multi_core/npusim_20261105121908_rms_norm_quant_2_multi_core/report/results/0000_rms_norm_quant_reports/0000_rms_norm_quant.npu-rep) |
| 3_vf | 8,780 | 32 | 160 | 5 | [Open](NPUSim_Prof_Live_Demo/results/rms_norm_quant_3_vf/npusim_20261105120957_rms_norm_quant_3_vf/report/results/0000_rms_norm_quant_reports/0000_rms_norm_quant.npu-rep) |
| 4_double_buffer | 7,746 | 32 | 160 | 5 | [Open](NPUSim_Prof_Live_Demo/results/rms_norm_quant_4_double_buffer/npusim_20261105121219_rms_norm_quant_4_double_buffer/report/results/0000_rms_norm_quant_reports/0000_rms_norm_quant.npu-rep) |
| 5_ub_utilization | 7,720 | 32 | 64 | 2 | [Open](NPUSim_Prof_Live_Demo/results/rms_norm_quant_5_ub_utilization/npusim_20261105121436_rms_norm_quant_5_ub_utilization/report/results/0000_rms_norm_quant_reports/0000_rms_norm_quant.npu-rep) |
| 6_binary_sum | 7,759 | 32 | 96 | 3 | [Open](NPUSim_Prof_Live_Demo/results/rms_norm_quant_6_binary_sum/npusim_20261105121642_rms_norm_quant_6_binary_sum/report/results/0000_rms_norm_quant_reports/0000_rms_norm_quant.npu-rep) |

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

## 1 → 2: распределить строки по всем векторным ядрам

«Строки независимы, поэтому вариант 2 распределяет их по всем 32 дорожкам AIV.
Полный отчёт подтверждает запуск: `ai_core_active=32` и 16 физических core ID,
каждый с AIV0 и AIV1. На любой дорожке видно более короткую последовательность
строк».

Выходных копирований стало **4
вместо 128**,
VF-вызовов на AIV — **13 вместо 385**.
Такты: **111,462 → 8,789** (12.68×).
Число событий смотрим по конкретной трассе, а сумму по всем ядрам — в сводке.

Исходник: [2_multi_core.asc](NPUSim_Prof_Live_Demo/cann-samples/Samples/2_Performance/rms_norm_quant_story/src/2_multi_core.asc).

## 2 → 5: объединить векторные вычисления и обрабатывать строки пачкой

«В варианте 2 много отдельных VF-вызовов и передач для каждой строки.
В варианте 5 держим больше вычислений вместе и обрабатываем пачку строк в UB.
На том же контексте VF-вызовов на AIV становится **2 вместо 13**.
Раскрываем PUSHQ, затем сравниваем MTE2/MTE3 и группы векторных загрузок/записей».

Входные копирования: **5
→ 2**; выходные:
**4 → 1**.
Такты: **8,789 → 7,720**,
снижение на **12.2%**.
Здесь одновременно меняются MicroAPI-вычисления, буферизация и работа пачкой;
весь выигрыш нельзя приписать одному из этих изменений. Буферизацию отдельно
смотрим на 3 → 4. Меньше DMA-команд не означает меньший объём входа и выхода.

Исходник: [5_ub_utilization.asc](NPUSim_Prof_Live_Demo/cann-samples/Samples/2_Performance/rms_norm_quant_story/src/5_ub_utilization.asc).

## Справочная таблица таймлайна: core 0 / AIV0

Числа посчитаны по Chrome traces для core 0 с удалением повторов по `instr_id`
внутри группы дорожек. Одна DMA-инструкция может отображаться на нескольких
слотах, поэтому число прямоугольников не обязательно равно числу инструкций.
Для DMA считаем `MOV_SRC_TO_DST_ALIGNv2`, исключая подготовку `MOV_SPR_XN`. `RV_VST` — отдельная
инструкция, а дорожка RVECST также содержит барьеры и маркеры завершения VF.

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

Произвольный пустой участок не называем измеренным stall. Меньше событий не
доказывает исчезновение всех зависимостей. Проверяем значения перекрытия и
сообщения каждого отчёта. Наличие PMU и SIMD sampling в новых записях:

| Variant | VF PMU rows | SIMD sampling rows |
| --- | ---: | ---: |
| 0 | 215 | 4096 |
| 1 | 215 | 3972 |
| 2 | 215 | 3757 |
| 3 | 215 | 3584 |
| 4 | 215 | 3511 |
| 5 | 215 | 3715 |
| 6 | 215 | 3397 |

Прежнее описание об отсутствии PMU-данных к этой серии уже не относится.

## Проверка результата и детекторы

Все семь численных проверок пройдены. Детекторы синхронизации и гонок отвечают
на другие вопросы; их результаты сохранены:

| Variant | Sync detector | Race detector |
| --- | --- | --- |
| 0 | [sync_instruction_detection] Found 3840 violation(s) — offending input lines: | [data_race_detection] No violations found. |
| 1 | [sync_instruction_detection] Found 2444 violation(s) — offending input lines: | [data_race_detection] No violations found. |
| 2 | [sync_instruction_detection] Found 2813 violation(s) — offending input lines: | [data_race_detection] No violations found. |
| 3 | [sync_instruction_detection] Found 3004 violation(s) — offending input lines: | [data_race_detection] No violations found. |
| 4 | [sync_instruction_detection] Found 3221 violation(s) — offending input lines: | [data_race_detection] No violations found. |
| 5 | [sync_instruction_detection] Found 852 violation(s) — offending input lines: | [data_race_detection] No violations found. |
| 6 | [sync_instruction_detection] Found 844 violation(s) — offending input lines: | [data_race_detection] No violations found. |

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
RUN="$DEMO_ROOT/results/rms_norm_quant_5_ub_utilization/npusim_20261105121436_rms_norm_quant_5_ub_utilization"
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
