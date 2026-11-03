# Скачать, перенести, распаковать и запустить

## На машине с доступом к GitHub

Нужны Git и Git LFS. Git LFS должен быть установлен до скачивания архива.
Например, на Ubuntu на машине с интернетом:

```bash
sudo apt-get install git-lfs
```

```bash
git lfs install
git clone https://github.com/alexChurkin/NPUSim_PerfDemo_20260511.git NPUSim_Demo_Distribution
cd NPUSim_Demo_Distribution
git lfs pull
sha256sum -c NPUSim_Prof_Live_Demo.tar.gz.sha256
```

Нужен настоящий архив (~483 МиБ), а не маленький текстовый LFS-указатель.
Проверка SHA-256 должна завершиться сообщением OK.

## На офлайн-машине

Перенесите два файла любым доступным способом:

- NPUSim_Prof_Live_Demo.tar.gz
- NPUSim_Prof_Live_Demo.tar.gz.sha256

Git, Git LFS и интернет на офлайн-машине не требуются. Нужны такой же CANN,
Linux x86_64, Python 3.9–3.12 с pip, CMake, make и cc.

В новом пустом каталоге с этими файлами:

```bash
sha256sum -c NPUSim_Prof_Live_Demo.tar.gz.sha256
tar -xzf NPUSim_Prof_Live_Demo.tar.gz
cd NPUSim_Prof_Live_Demo
export CANN_SETENV=/actual/path/to/cann/bin/setenv.bash
bash demo.sh
```

В меню введите номера вариантов через пробел, например 2 4 5.
Команда p 2 4 показывает точные команды без симуляции; q закрывает меню.
Если нужна сборка, она выполнится автоматически без интернета.

Полный автоматический прогон 1 → 2 → 4 → 5 → 6:

```bash
bash start.sh
```

Выбор вариантов без меню:

```bash
bash demo.sh 2 4 5
```

Внутри архива уже есть оба репозитория, NumPy wheels, скрипты и готовые профили.
Порядок показа, метрики, хинты и ограничения описаны в DEMO.md.

## Если перенос большого файла неудобен

На машине с архивом можно разбить его на части:

```bash
split -b 100M -d -a 2 NPUSim_Prof_Live_Demo.tar.gz NPUSim_Prof_Live_Demo.tar.gz.part-
```

Перенесите все части вместе с исходным файлом .sha256.
На целевой машине соберите и проверьте архив:

```bash
cat NPUSim_Prof_Live_Demo.tar.gz.part-* > NPUSim_Prof_Live_Demo.tar.gz
sha256sum -c NPUSim_Prof_Live_Demo.tar.gz.sha256
```

После этого используйте команды распаковки выше. Отдельно скачивать и вручную
раскладывать исходники и зависимости не требуется.
