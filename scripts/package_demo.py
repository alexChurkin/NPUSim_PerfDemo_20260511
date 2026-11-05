#!/usr/bin/env python3
"""Package one verified November 5 recording per variant, excluding old profiles."""
import hashlib
import json
from pathlib import Path
import sqlite3
import struct
import tarfile

REPO = Path(__file__).resolve().parent.parent
ROOT = REPO / 'NPUSim_Prof_Live_Demo'
BUILD = '20261104000324968'
VARIANTS = ('0_naive', '1_preload_gamma', '2_multi_core', '3_vf',
            '4_double_buffer', '5_ub_utilization', '6_binary_sum')


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def validate_rep(data):
    magic, version, origin, head, count, entry, _, length = struct.unpack_from('<8sIHHIIIQ', data)
    assert (magic, version, origin, head, entry, length) == (
        b'npu-rep\0', 0x10000, 1, 36, 160, len(data))
    offset = head + count * entry
    names = set()
    for i in range(count):
        mark, name, kind, _, _, size, start = struct.unpack_from('<8s128sHHIQQ', data, head + i * entry)
        assert mark == magic and name not in names and start == offset and size > 0
        names.add(name)
        offset = start + size
        assert offset <= len(data)
        payload = data[start:offset]
        if kind == 1:
            validate_rep(payload)
        elif kind == 2:
            json.loads(payload)
        elif kind == 3:
            for line in payload.splitlines():
                if line.strip():
                    json.loads(line)
    assert offset == len(data)


def main():
    items = json.loads((ROOT / 'latest-measurements.json').read_text())
    by_name = {item['variant']: item for item in items}
    assert set(by_name) == {'rms_norm_quant_' + v for v in VARIANTS}
    selected = []
    logs = set()
    records = []
    for variant in VARIANTS:
        item = by_name['rms_norm_quant_' + variant]
        run = ROOT / item['run']
        assert run.name.startswith('npusim_20261105'), run
        assert item.get('precision_ok'), f'Precision not verified: {run}'
        log = ROOT / item['console_log']
        text = log.read_text()
        assert BUILD in text and 'Compare Difference length 0' in text, log
        assert 'Demo shape: a=128 r=256' in text, log
        assert 'RSS limit 12288 MiB, available memory reserve 1536 MiB' in text, log
        assert 'NPU SIM auto generate report succeeded!' in text, log
        databases = list((run / 'record').glob('*.db'))
        assert databases, f'Missing raw recording: {run}'
        for db in databases:
            with sqlite3.connect(db.resolve().as_uri() + '?mode=ro', uri=True) as conn:
                assert conn.execute('PRAGMA quick_check').fetchone() == ('ok',), db
        reports = [ROOT / p for p in item['artifacts']['archives']]
        assert len(reports) == 1 and item['artifacts']['vf'] and item['artifacts']['traces'], run
        for report in reports:
            validate_rep(report.read_bytes())
        selected.append(Path(item['run']))
        logs.add(Path(item['console_log']))
        records.append({
            'variant': item['variant'], 'run': item['run'],
            'console_log': item['console_log'], 'precision_ok': True,
            'launch_core_cap': 1 if int(variant[0]) < 2 else 2,
            'kernel_info': item['summaries'][0]['data']['kernel_info'],
            'detections': item.get('detections', {}),
            'reports': [{'path': str(p.relative_to(ROOT)), 'sha256': digest(p)} for p in reports],
        })
    manifest = {'schema_version': 1, 'recorded_on': '2026-11-05', 'cann_version': '9.3.0',
                'cann_build': BUILD, 'cann_internal_version': 'V100R001C13B046',
                'shape': [128, 256], 'launch_core_cap': 2, 'report_cores': [0],
                'cpu_affinity_slots': 2, 'model_worker_threads': 2,
                'rss_limit_mib': 12288, 'memory_reserve_mib': 1536,
                'timeout_seconds': {'0': 3600, '1': 3600, '2': 900, '3': 3600,
                                    '4': 3600, '5': 900, '6': 3600},
                'runs': records}
    (ROOT / 'recording-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    # Publish only this suite in the measurement index. Old local runs stay on disk.
    (ROOT / 'measurements.json').write_text(json.dumps(
        [by_name['rms_norm_quant_' + v] for v in VARIANTS], indent=2, ensure_ascii=False) + '\n')

    output = REPO / 'NPUSim_Prof_Live_Demo.tar.gz'
    temporary = output.with_name(output.name + '.tmp')
    excluded = {'build', 'results', 'logs', '.cache', '.development'}

    def filter_entry(info):
        parts = Path(info.name).parts
        if any(p in {'.git', '__pycache__', '.pytest_cache'} for p in parts):
            return None
        if info.name.endswith(('.pyc', '.tmp')) or '.tmp.' in Path(info.name).name:
            return None
        return info

    with tarfile.open(temporary, 'w:gz', compresslevel=6) as archive:
        archive.add(ROOT, arcname=ROOT.name, recursive=False)
        for child in sorted(ROOT.iterdir()):
            if child.name in excluded or child.name.startswith('build.previous.'):
                continue
            archive.add(child, arcname=f'{ROOT.name}/{child.name}', filter=filter_entry)
        for run in selected:
            archive.add(ROOT / run, arcname=f'{ROOT.name}/{run}', filter=filter_entry)
        for log in sorted(logs | {Path('logs/build.log'), Path('logs/build.console.log'),
                                  Path('logs/summary.log')}):
            if (ROOT / log).is_file():
                archive.add(ROOT / log, arcname=f'{ROOT.name}/{log}')
    with tarfile.open(temporary) as archive:
        names = archive.getnames()
        archived_runs = {str(Path(*Path(n).parts[1:4])) for n in names
                         if n.startswith(ROOT.name + '/results/')}
        assert archived_runs == {str(run) for run in selected}, archived_runs
        assert sum(n.endswith('.npu-rep') for n in names) == 7
        assert not any('/npusim_20261103' in n for n in names)
    checksum = digest(temporary)
    temporary.replace(output)
    (REPO / (output.name + '.sha256')).write_text(checksum + '  ' + output.name + '\n')
    print(f'Packaged {len(records)} verified recordings: {output.stat().st_size:,} bytes')
    print('SHA-256:', checksum)


if __name__ == '__main__':
    main()
