#!/usr/bin/env python3
"""Reject relocated builds and builds configured for a different CANN."""
import os
import pathlib
import sys

build, source = map(pathlib.Path, sys.argv[1:])
try:
    cache = (build / 'CMakeCache.txt').read_text()
except OSError:
    sys.exit(1)
values = dict(line.split('=', 1) for line in cache.splitlines() if '=' in line)
toolkit = os.environ.get('ASCEND_HOME_PATH')
cached_toolkit = values.get('ASCEND_CANN_PACKAGE_PATH:PATH')
ok = (values.get('CMAKE_CACHEFILE_DIR:INTERNAL') == str(build.resolve()) and
      values.get('CMAKE_HOME_DIRECTORY:INTERNAL') == str(source.resolve()) and
      toolkit is not None and cached_toolkit is not None and
      pathlib.Path(toolkit).resolve() == pathlib.Path(cached_toolkit).resolve())
sys.exit(0 if ok else 1)
