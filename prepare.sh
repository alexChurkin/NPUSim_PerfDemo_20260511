#!/usr/bin/env bash
# Retrieve the original, checksummed package and apply versioned launch fixes.
set -eo pipefail
repo=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$repo"
archive=NPUSim_Prof_Live_Demo.tar.gz
package=NPUSim_Prof_Live_Demo
if [[ ! -d "$package" ]]; then
    if [[ ! -f "$archive" ]] || head -c 100 "$archive" | grep -q '^version https://git-lfs.github.com/spec/v1'; then
        echo 'Downloading demo archive; Git LFS is optional...'
        revision=main
        if [[ -e "$repo/.git" ]]; then
            revision=$(git rev-parse HEAD)
        fi
        curl -fL --retry 3 --progress-bar \
            "https://media.githubusercontent.com/media/alexChurkin/NPUSim_PerfDemo_20260511/$revision/$archive" \
            -o "$archive.tmp"
        expected=$(awk '{print $1}' "$archive.sha256")
        printf '%s  %s\n' "$expected" "$archive.tmp" | sha256sum -c -
        mv "$archive.tmp" "$archive"
    fi
    sha256sum -c "$archive.sha256"
    # Extract into a staging directory so interrupted extraction can be retried.
    staging=$(mktemp -d "$repo/.demo-extract.XXXXXX")
    trap 'rm -rf -- "$staging"' EXIT
    tar -xzf "$archive" -C "$staging"
    mv "$staging/$package" "$package"
    rmdir "$staging"
    trap - EXIT
fi
[[ -f "$package/start.sh" && -f "$package/demo/env.sh" ]] || {
    echo "Incomplete package: $package. Move it aside and retry prepare.sh." >&2
    exit 1
}
# Only maintain launch/build wrappers; preserve sources and saved recordings.
for file in "$repo"/compatibility/demo/*.sh "$repo"/compatibility/demo/*.py; do
    target="$package/demo/$(basename "$file")"
    if ! cmp -s "$file" "$target"; then
        # A long-running bash process may still be reading the previous inode.
        # Rename a complete replacement so that process can finish safely.
        replacement=$(mktemp "$target.tmp.XXXXXX")
        cp -p "$file" "$replacement"
        mv "$replacement" "$target"
    fi
done
# Keep the V100 AIV lane count used by the Small Grid hint aligned with the
# report's 32-lane capacity. The archive already includes this fix; the overlay
# also applies it to packages extracted from earlier revisions.
source_file="$repo/compatibility/npusim/small_grid_hint.py"
target="$package/npu-simulator/npusim/prof/src/backend/hints/small_grid_hint.py"
if ! cmp -s "$source_file" "$target"; then
    replacement=$(mktemp "$target.tmp.XXXXXX")
    cp -p "$source_file" "$replacement"
    mv "$replacement" "$target"
fi
