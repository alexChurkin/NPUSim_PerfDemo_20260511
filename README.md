# NPUSim Prof Live Demo

Офлайн-комплект для демонстрации профилирования RMSNorm на Ascend950.
Архив хранится в **Git LFS**. Внутри: npu-simulator, cann-samples, NumPy wheels,
сборка без сети, интерактивное меню и готовые профили.

На машине с доступом к GitHub, где установлены Git и Git LFS:

```bash
git lfs install
git clone https://github.com/alexChurkin/NPUSim_PerfDemo_20260511.git NPUSim_Demo_Distribution
cd NPUSim_Demo_Distribution
git lfs pull
sha256sum -c NPUSim_Prof_Live_Demo.tar.gz.sha256
```

Для офлайн-машины достаточно перенести архив и файл `.sha256`.
На ней выполнить:

```bash
sha256sum -c NPUSim_Prof_Live_Demo.tar.gz.sha256
tar -xzf NPUSim_Prof_Live_Demo.tar.gz
cd NPUSim_Prof_Live_Demo
export CANN_SETENV=/actual/path/to/cann/bin/setenv.bash
bash demo.sh
```

Нужны тот же CANN, Linux x86_64, Python 3.9–3.12 с pip, CMake, make и cc.
Самой демке интернет не нужен.

Полный автоматический прогон: `bash start.sh` из распакованного каталога.
Выбор вариантов без меню: `bash demo.sh 2 4 5`.
Просмотр команд: `bash demo.sh --dry-run 2 4 5`.

[Полный гайд по скачиванию и распаковке](DOWNLOAD.md).
[Сценарий показа, метрики и хинты](DEMO.md).
