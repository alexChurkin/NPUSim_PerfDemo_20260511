# NPUSim Prof Live Demo

An offline RMSNorm profiling demo for Ascend950. The archive is stored in **Git LFS**.
It includes npu-simulator, cann-samples, NumPy wheels, an offline build workflow,
an interactive launcher, and recorded profiles.

On a machine with GitHub access and Git LFS installed:

```bash
git lfs install
GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 https://github.com/alexChurkin/NPUSim_PerfDemo_20260511.git NPUSim_Demo_Distribution
cd NPUSim_Demo_Distribution
git -c lfs.forceprogress=true lfs pull
sha256sum -c NPUSim_Prof_Live_Demo.tar.gz.sha256
```

Transfer the archive and its `.sha256` file to the offline target. Then run:

```bash
sha256sum -c NPUSim_Prof_Live_Demo.tar.gz.sha256
tar -xzf NPUSim_Prof_Live_Demo.tar.gz
cd NPUSim_Prof_Live_Demo
export CANN_SETENV=/actual/path/to/cann/bin/setenv.bash
bash demo.sh
```

The target needs the same CANN installation, Linux x86_64, Python 3.9–3.12 with pip,
CMake, make, and cc. The demo itself does not need Internet access.

Full automatic build and main sequence: `bash start.sh`.
Selected variants: `bash demo.sh 2 4 5`.
Command preview: `bash demo.sh --dry-run 2 4 5`.

[Download, extraction, and offline transfer guide](DOWNLOAD.md).
[Presentation order, measurements, and hints](DEMO.md).

## Update an existing installation to English

If the full package is already extracted, download the small
[English documentation and launcher update](NPUSim_Prof_Live_Demo_English_Update.tar.gz).
From inside the extracted demo directory:

```bash
tar -xzf /path/to/NPUSim_Prof_Live_Demo_English_Update.tar.gz --strip-components=1
bash demo.sh --list
```

This updates the demo documentation and launcher captions without downloading
the full archive again. It does not change kernels or recorded measurements.
The current full archive also includes the English documentation and launcher.
