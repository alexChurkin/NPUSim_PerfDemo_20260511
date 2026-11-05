#!/usr/bin/env python3
"""Select the newest installed CANN by package version and build timestamp."""
import pathlib
import platform
import re
import sys


def version_key(setenv):
    for parent in setenv.parents:
        info = parent / 'compiler/version.info'
        if info.is_file():
            text = info.read_text()
            version = re.search(r'^Version=(.*)$', text, re.M)
            timestamp = re.search(r'^timestamp=(.*)$', text, re.M)
            return (tuple(map(int, re.findall(r'\d+', version[1]))) if version else (),
                    re.sub(r'\D', '', timestamp[1]) if timestamp else '', str(setenv))
    return (), '', str(setenv)


def select(roots):
    arch = platform.machine()
    patterns = ('cann/bin/setenv.bash', 'cann-*/bin/setenv.bash',
                f'cann-*/{arch}-linux/bin/setenv.bash',
                f'*/cann-*/{arch}-linux/bin/setenv.bash',
                'ascend-toolkit/*/bin/setenv.bash', 'latest/bin/setenv.bash')
    candidates = {p.resolve() for root in roots for pattern in patterns
                  for p in root.glob(pattern) if p.is_file()}
    if not candidates:
        raise SystemExit('CANN not found. Set CANN_SETENV=/path/to/bin/setenv.bash')
    return max(candidates, key=version_key)


if __name__ == '__main__':
    roots = [pathlib.Path(p) for p in sys.argv[1:]] or [
        pathlib.Path('/usr/local/Ascend'), pathlib.Path.home() / 'Ascend']
    print(select(roots))
