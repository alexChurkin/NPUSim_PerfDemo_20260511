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

Git stores one LFS archive plus documentation. The extracted workspace is ignored;
sources, runtime, and profiles are contained in the archive instead of duplicated in Git.
After a Git clone, run `git lfs pull` to retrieve the archive.
