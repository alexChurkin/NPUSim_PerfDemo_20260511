# Optional GitCode LFS distribution

The primary distribution repository is
https://github.com/alexChurkin/NPUSim_PerfDemo_20260511.
Use [DOWNLOAD.md](DOWNLOAD.md) to download the current package.
The GitCode upload was not completed; this document preserves instructions for
using GitCode as an alternative distribution host.

The archive is stored through Git LFS. Documentation and the checksum file use
ordinary Git storage. Git LFS is only needed on the machine downloading the package;
the offline target receives the actual archive.

## Download after a GitCode distribution has been published

Install Git LFS on a connected machine, for example on Ubuntu:

```bash
sudo apt-get install git-lfs
git lfs version
git lfs install
```

Once the archive has been published to the GitCode repository:

```bash
export GITCODE_REPO_URL='https://gitcode.com/churkinaleksandr/NPUSim_Prof_Live_Demo.git'
GIT_LFS_SKIP_SMUDGE=1 git clone "$GITCODE_REPO_URL" NPUSim_Demo_Distribution
cd NPUSim_Demo_Distribution
git -c lfs.forceprogress=true lfs pull
git lfs ls-files
sha256sum -c NPUSim_Prof_Live_Demo.tar.gz.sha256
```

Private repositories require normal GitCode authentication. Do not put tokens
in commands or documentation. Verification must report `OK`. A small text LFS
pointer is not the archive; retrieve the object with `git lfs pull`.
Do not rely on a website's source ZIP to contain the actual LFS object.

## Transfer, extract, and run offline

Transfer `NPUSim_Prof_Live_Demo.tar.gz` and its `.sha256` file.
The target needs the same CANN installation, Linux x86_64, Python 3.9–3.12 with pip,
CMake, make, and cc. Git, Git LFS, and Internet access are not required on the target.

In a new empty directory containing the two files:

```bash
sha256sum -c NPUSim_Prof_Live_Demo.tar.gz.sha256
tar -xzf NPUSim_Prof_Live_Demo.tar.gz
cd NPUSim_Prof_Live_Demo
export CANN_SETENV=/actual/path/to/cann/bin/setenv.bash
bash demo.sh
```

Selected variants: `bash demo.sh 2 4 5`.
Command preview: `bash demo.sh --dry-run 2 4 5`.
Full build and main sequence: `bash start.sh`.
Offline NumPy installation and compilation are automatic. Profiles go to `results/`,
commands and logs to `logs/`. See [DEMO.md](DEMO.md) for the presentation guide.

## Publish or update a distribution through LFS

On the authoring machine, rebuild the archive and checksum:

```bash
cd /path/to/NPUSim_Prof_Live_Demo
bash demo/pack.sh
```

Copy the two updated files into the distribution repository, then run:

```bash
git lfs install --local
git lfs track 'NPUSim_Prof_Live_Demo.tar.gz'
git add .gitattributes NPUSim_Prof_Live_Demo.tar.gz NPUSim_Prof_Live_Demo.tar.gz.sha256
git commit -m 'Update offline NPUSim profiling demo'
git lfs ls-files
git push
```

Configure LFS tracking before adding the archive to its first commit.
These commands do not rewrite existing ordinary Git history.
