# Получение демо из GitCode LFS и офлайн-запуск

Основной выбранный репозиторий — https://github.com/alexChurkin/NPUSim_PerfDemo_20260511.
Для скачивания используйте [DOWNLOAD.md](DOWNLOAD.md). Публикация в GitCode не завершена;
ниже сохранены инструкции для его возможного использования как резервного хранилища.

В репозитории дистрибутива большой архив хранится через Git LFS. Файл контрольной суммы,
этот гайд и README хранятся обычным Git. Для работы самой демки Git LFS не нужен:
на офлайн-машину переносится уже скачанный архив.

## 1. Скачать на машине с доступом к GitCode

Нужны Git и Git LFS. На Ubuntu с доступом к пакетным репозиториям:

```bash
sudo apt-get install git-lfs
git lfs version
git lfs install
```

Укажите URL репозитория дистрибутива, затем скачайте файлы:

```bash
export GITCODE_REPO_URL='https://gitcode.com/churkinaleksandr/NPUSim_Prof_Live_Demo.git'
git clone "$GITCODE_REPO_URL" NPUSim_Demo_Distribution
cd NPUSim_Demo_Distribution
git lfs pull
git lfs ls-files
sha256sum -c NPUSim_Prof_Live_Demo.tar.gz.sha256
```

Для закрытого репозитория потребуется
обычная авторизация GitCode; токены не нужно записывать в команды или гайд.

Результат проверки должен быть `NPUSim_Prof_Live_Demo.tar.gz: OK`.
Если вместо архива загружен маленький текстовый LFS-указатель, проверка не пройдёт:
выполните `git lfs pull` на машине с доступом к GitCode.
Не полагайтесь на ZIP исходников с веб-страницы репозитория как на способ скачать LFS-объект.

## 2. Перенести на удалённую машину без интернета

Перенести эти **два файла** любым доступным способом (scp, флешка, внутренний файловый ресурс):

```text
NPUSim_Prof_Live_Demo.tar.gz
NPUSim_Prof_Live_Demo.tar.gz.sha256
```

Git, Git LFS и доступ к GitCode на офлайн-машине не требуются.
На ней уже должны быть тот же CANN, Linux x86_64, Python 3.9–3.12 с pip, CMake, make и cc.
NumPy wheels и исходники обоих репозиториев включены в архив.

## 3. Проверить, распаковать и запустить

В каталоге с перенесёнными файлами:

```bash
sha256sum -c NPUSim_Prof_Live_Demo.tar.gz.sha256
tar -xzf NPUSim_Prof_Live_Demo.tar.gz
cd NPUSim_Prof_Live_Demo
export CANN_SETENV=/actual/path/to/cann/bin/setenv.bash
```

Перед распаковкой обновлённой версии используйте новый пустой каталог,
чтобы не смешать её со старой сборкой и результатами.

Интерактивная демонстрация с выбором вариантов:

```bash
bash demo.sh
```

Без меню, выбранные варианты:

```bash
bash demo.sh 2 4 5
```

Показать команды без симуляции:

```bash
bash demo.sh --dry-run 2 4 5
```

Полностью собрать и запустить 1 → 2 → 4 → 5 → 6:

```bash
bash start.sh
```

Подготовка NumPy и сборка выполняются офлайн. Профили сохраняются в `results/`,
команды и логи — в `logs/`. Готовые профили для показа уже включены.
Порядок показа и измеренные хинты описаны в [DEMO.md](DEMO.md).

## 4. Обновить дистрибутив через LFS

На машине автора сначала пересобрать архив и контрольную сумму:

```bash
cd /path/to/NPUSim_Prof_Live_Demo
bash demo/pack.sh
```

В локальном клоне репозитория дистрибутива, после копирования новых двух файлов:

```bash
git lfs install --local
git lfs track 'NPUSim_Prof_Live_Demo.tar.gz'
git add .gitattributes NPUSim_Prof_Live_Demo.tar.gz NPUSim_Prof_Live_Demo.tar.gz.sha256
git commit -m 'Update offline NPUSim profiling demo'
git lfs ls-files
git push
```

Правило LFS должно быть установлено **до первого добавления архива в коммит**.
Уже существующую историю обычного Git эти команды не переписывают.
