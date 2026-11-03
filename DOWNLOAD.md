# Download, transfer, extract, and run

## Download on a machine with GitHub access

Install Git and Git LFS before downloading the archive. For example, on Ubuntu
with access to package repositories:

```bash
sudo apt-get install git-lfs
```

Clone the small Git repository first, then download the archive with visible progress:

```bash
git lfs install
GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 https://github.com/alexChurkin/NPUSim_PerfDemo_20260511.git NPUSim_Demo_Distribution
cd NPUSim_Demo_Distribution
git -c lfs.forceprogress=true lfs pull
sha256sum -c NPUSim_Prof_Live_Demo.tar.gz.sha256
```

`GIT_LFS_SKIP_SMUDGE=1` disables automatic archive downloads during cloning.
The separate `git lfs pull` step displays download progress.
If an ordinary clone appears stuck after `Resolving deltas: 100%`, it may already
be downloading the LFS archive during checkout. Press Ctrl+C and repeat the commands
above using a new directory; the old directory does not need to be deleted.

You need the actual archive (approximately 483 MiB), rather than a small text LFS pointer.
Checksum verification must print `NPUSim_Prof_Live_Demo.tar.gz: OK`.

## Transfer to the offline machine

Transfer these two files using scp, a USB drive, or an internal file share:

- `NPUSim_Prof_Live_Demo.tar.gz`
- `NPUSim_Prof_Live_Demo.tar.gz.sha256`

The offline machine does not need Git, Git LFS, or Internet access.
It needs the same CANN installation, Linux x86_64, Python 3.9–3.12 with pip,
CMake, make, and cc. NumPy wheels and both source repositories are included.

## Verify, extract, and launch

Use a new empty directory when extracting an updated version, so it does not mix
with an older build or results. In the directory containing the transferred files:

```bash
sha256sum -c NPUSim_Prof_Live_Demo.tar.gz.sha256
tar -xzf NPUSim_Prof_Live_Demo.tar.gz
cd NPUSim_Prof_Live_Demo
export CANN_SETENV=/actual/path/to/cann/bin/setenv.bash
bash demo.sh
```

Enter variant numbers separated by spaces, for example `2 4 5`.
Use `p 2 4` to preview commands without simulation, or `q` to exit.
The launcher installs NumPy from local wheels and builds offline when needed.

To build and run the complete sequence 1 → 2 → 4 → 5 → 6:

```bash
bash start.sh
```

To run selected variants without the menu:

```bash
bash demo.sh 2 4 5
```

Recorded profiles are already included in the full archive. New profiles go to `results/`,
and commands and console logs go to `logs/`. See [DEMO.md](DEMO.md) for the presentation
order, measured results, hints, and known profiling limitations.

## Transfer the archive in smaller parts

On the machine containing the archive:

```bash
split -b 100M -d -a 2 NPUSim_Prof_Live_Demo.tar.gz NPUSim_Prof_Live_Demo.tar.gz.part-
```

Transfer all parts together with the original `.sha256` file. Reassemble and verify:

```bash
cat NPUSim_Prof_Live_Demo.tar.gz.part-* > NPUSim_Prof_Live_Demo.tar.gz
sha256sum -c NPUSim_Prof_Live_Demo.tar.gz.sha256
```

Then use the extraction commands above. Sources and dependencies do not need
to be downloaded and arranged individually.
