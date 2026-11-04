# NPUSim profiling demo — complete English package

Download **NPUSim_Prof_Live_Demo.tar.gz**. This is the only demo archive;
it includes English documentation, all seven examples, saved profiles, and Python/NumPy.

```bash
sha256sum -c NPUSim_Prof_Live_Demo.tar.gz.sha256
tar -xzf NPUSim_Prof_Live_Demo.tar.gz
cd NPUSim_Prof_Live_Demo
bash start.sh
```

No interactive menus. CANN 9.3.0 with the Ascend950 simulator and host build tools are required.
To view saved results, open `NPUSim_Prof_Live_Demo/RESULTS.html` in a browser.
Start with `NPUSim_Prof_Live_Demo/START_HERE.md` after extraction.

[Presentation walkthrough](DEMO_STORY.md): four reports, 0 → 1 → 2 → 5,
with the narration, timeline capture instructions, screenshot positions, and commands.
Its source/profile links resolve after extracting the package.
The walkthrough is also included inside the archive as `DEMO_STORY.md`.

For `.npu-rep` viewing, install the VS Code `.vsix` from
[the profiling extension releases](https://gitcode.com/opdevtools/plugin_release/releases/) using **Install from VSIX…**.

Tested environment: **CANN 9.3.0**, build `20261028000328247`
([matching download](https://ascend.devcloud.huaweicloud.com/artifactory/cann-run-mirror/software/master/20261028000328247/));
npu-simulator base `1185ddf016a0e3563c0d3af80305d7ea78c81fe9`;
cann-samples base `5c6e28cc7fce6fbeb9b67befcde98a6a4dc492ed`.
[Viewer setup and exact source links](DEMO_STORY.md#viewer-and-tested-environment)
are documented alongside the launch commands.

Git stores one LFS archive plus documentation. The extracted workspace is ignored;
sources, runtime, and profiles are contained in the archive instead of duplicated in Git.
After a Git clone, run `git lfs pull` to retrieve the archive.
