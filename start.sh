#!/usr/bin/env bash
# Entry point for a fresh checkout, including checkouts without Git LFS.
set -eo pipefail
repo=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
bash "$repo/prepare.sh"
exec bash "$repo/NPUSim_Prof_Live_Demo/start.sh" "$@"
