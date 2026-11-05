#!/usr/bin/env python3
"""Collect completed run artifacts without changing simulation databases."""
import json
import os
from pathlib import Path
import sqlite3
import re

root = Path(os.environ.get('DEMO_ROOT', Path(__file__).resolve().parent.parent))
results = Path(os.environ.get('RESULTS_DIR', root / 'results'))
collected = []
for variant in sorted(results.glob('rms_norm_quant_*')):
    runs = sorted(variant.glob('npusim_*'))
    for run in runs:
        summaries = list(run.glob('report/**/summary.json'))
        if not summaries:
            continue
        item = {'variant': variant.name, 'run': os.path.relpath(run, root),
                'summaries': [], 'hints': [], 'hint_status': [], 'artifacts': {}}
        for path in summaries:
            item['summaries'].append({'path': os.path.relpath(path, root), 'data': json.loads(path.read_text())})
        item['analysis_limitations'] = []
        for log in run.glob('report/**/runner.py.log'):
            item['analysis_limitations'] += [line for line in log.read_text(errors='replace').splitlines()
                if 'analysis failed:' in line or 'hint failed:' in line]
        for log in (root / 'logs').glob(variant.name + '_*.log'):
            text = log.read_text(errors='replace')
            if run.name not in text:
                continue
            duration = re.search(r'USER_APP executed successfully in ([0-9.]+)s', text)
            item['simulation_seconds'] = float(duration.group(1)) if duration else None
            item['precision_ok'] = 'Compare Difference length 0' in text
            item['console_log'] = os.path.relpath(log, root)
            helper = re.search(r'cannsim_helper enabled: (.+)', text)
            if helper:
                item['helper_library'] = helper.group(1).strip()
                build = re.search(r'/(\d{17})/cann-[^/]+/', item['helper_library'])
                if build:
                    item['cann_build'] = build.group(1)
        item['collection_rows'] = {}
        for path in run.glob('record/*.db'):
            with sqlite3.connect(f'{path.resolve().as_uri()}?mode=ro', uri=True) as db:
                for table in ('MemoryHeatmapLayout', 'MemoryHeatmapCells', 'SIMDSamplingStats',
                              'VfPMUMetrics', 'PMUScalarCounters'):
                    try:
                        item['collection_rows'][table] = db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
                    except sqlite3.Error:
                        pass
        item['detections'] = {}
        for key in ('sync_instruction_detection', 'data_race_detection'):
            path = run / 'report' / (key + '_report.txt')
            if path.is_file():
                header = path.read_text(errors='replace').splitlines()[0]
                item['detections'][key] = header
        for pattern, key in [('**/*vf_report.json', 'vf'), ('**/trace_core*.json*', 'traces'),
                             ('**/*.npu-rep', 'archives')]:
            item['artifacts'][key] = [os.path.relpath(p, root) for p in run.glob(pattern)]
        for path in run.glob('**/*.db'):
            with sqlite3.connect(f'{path.resolve().as_uri()}?mode=ro', uri=True) as db:
                tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if 'HintTypes' not in tables:
                    continue
                item['hint_status'] += [dict(zip(('type', 'passed'), r)) for r in db.execute(
                    'SELECT HintTypeName, HintPassed FROM HintTypes')]
                for table in ('KernelHints', 'InstructionHints', 'SourceLineHints'):
                    if table not in tables:
                        continue
                    query = f'''SELECT DISTINCT t.HintTypeName, m.HintMsgText
                        FROM {table} h JOIN HintTypes t ON h.HintTypeId=t.HintTypeId
                        JOIN HintMessages m ON h.HintMsgId=m.HintMsgId'''
                    for name, message in db.execute(query):
                        hint = {'type': name, 'message': message, 'scope': table}
                        if hint not in item['hints']:
                            item['hints'].append(hint)
        collected.append(item)
output = root / 'measurements.json'
output.write_text(json.dumps(collected, indent=2, ensure_ascii=False) + '\n')
for item in collected:
    print(item['variant'], item['run'])
    for summary in item['summaries']:
        print('  kernel:', summary['data'].get('kernel_info'))
    print('  hints:', ', '.join(sorted({h['type'] for h in item['hints']})))
    print('  artifacts:', {k: len(v) for k, v in item['artifacts'].items()})
print(output)

# A self-contained offline landing page: no server, JavaScript, or menu.
import html
latest_by_variant = {}
for item in collected:
    latest_by_variant[item['variant']] = item
latest = list(latest_by_variant.values())
(root / 'latest-measurements.json').write_text(
    json.dumps(latest, indent=2, ensure_ascii=False) + '\n')

def link(path, label):
    return '<a href="' + html.escape(path, quote=True) + '">' + html.escape(label) + '</a>'

rows = []
sections = []
for item in latest:
    name = item['variant']
    short = name.removeprefix('rms_norm_quant_')
    info = item['summaries'][0]['data'].get('kernel_info', {})
    clocks = info.get('kernel_total_clocks', 'unknown')
    passed = item.get('precision_ok', False)
    precision = 'PASS' if passed else 'NOT VERIFIED'
    seconds = item.get('simulation_seconds', 'unknown')
    artifacts = item['artifacts']
    summary = item['summaries'][0]['path']
    console = item.get('console_log')
    traces = artifacts.get('traces', [])
    vf = artifacts.get('vf', [])
    source = 'cann-samples/Samples/2_Performance/rms_norm_quant_story/src/' + short + '.asc'
    trace = next((p for p in traces if '/core_0/' in p), traces[0] if traces else None)
    links = [link(summary, 'Summary'), link(source, 'Kernel source')]
    if console:
        links.append(link(console, 'Console log'))
    if trace:
        links.append(link(trace, 'Core 0 timeline'))
    if vf:
        links.append(link(vf[0], 'VF report'))
    for archive in artifacts.get('archives', []):
        links.append(link(archive, 'Viewer report (.npu-rep)'))
    rows.append('<tr><td>' + html.escape(short) + '</td><td>' + precision + '</td><td>'
        + str(clocks) + '</td><td>' + str(seconds) + '</td><td>' + ' · '.join(links) + '</td></tr>')
    diagnostics = item.get('detections', {})
    limitations = item.get('analysis_limitations', [])
    runlog = root / item['run'] / 'report/results/runner.py.log'
    warnings = []
    if runlog.exists():
        warnings = sorted({line for line in runlog.read_text(errors='replace').splitlines()
            if 'without register payload' in line or 'fallback' in line.lower()})
    sections.append('<h2>' + html.escape(short) + '</h2><p>' + link(item['run'] + '/', 'Profile directory')
        + '</p><p>Collected ' + str(len(traces)) + ' timelines and ' + str(len(vf)) + ' VF report(s).</p>'
        + '<p>' + '<br>'.join(html.escape(k + ': ' + v) for k, v in diagnostics.items()) + '</p>'
        + ('<p>Analysis limitations: ' + html.escape('; '.join(limitations)) + '</p>' if limitations else '')
        + ('<p>Custom SIMD regions: some RV_VBR register payloads were not collected. '
           'Other analyses continue; details are recorded in runner.py.log.</p>' if warnings else ''))
page = '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NPUSim — all seven profiling examples</title>
<style>body{font:16px/1.5 system-ui,sans-serif;max-width:1250px;margin:40px auto;padding:0 24px;color:#17212b;background:#fafbfd}h1{line-height:1.2}table{border-collapse:collapse;width:100%;background:white}th,td{text-align:left;padding:13px;border-bottom:1px solid #d7dfe7;vertical-align:top}th{background:#e9eef4}a{color:#0756a1}code{background:#e9eef4;padding:2px 5px}h2{margin-top:36px}p{max-width:1050px}</style>
<h1>NPUSim: all seven examples</h1>
<p>RMSNorm + quantization · Ascend950 · 128 × 256 · timing simulation.</p>
<p>Variants 0–1 intentionally use one AIV. Variants 2–6 record all 32 AIV lanes
as 16 physical core timelines (AIV0 and AIV1 per ID). Exact settings for the packaged release
are in <a href="recording-manifest.json">recording provenance</a>;
per-run paths and detected CANN builds are in <a href="latest-measurements.json">the measurement index</a>.</p>
<p>These are saved results. You can read this page offline without running the simulator.</p>
<p>To run everything again: <code>bash start.sh</code>. No menus or additional downloads.
CANN 9.3.0 and host build tools are required; Python and NumPy are included.</p>
<p><a href="README.md">Setup and commands</a> · <a href="DEMO_STORY.md">English walkthrough</a> ·
<a href="DEMO_STORY_RU.md">Русский сценарий</a> · <a href="latest-measurements.json">Machine-readable results</a></p>
<table><thead><tr><th>Variant</th><th>Precision</th><th>Kernel clocks</th><th>Simulation seconds</th><th>Open artifacts</th></tr></thead><tbody>'''
page += '\n'.join(rows) + '''</tbody></table>
<p>Precision PASS: every output is within the original absolute int8 tolerance of 1.
Kernel clocks measure simulated device time. Simulation seconds are host wall time.</p>
<p>For pipeline inspection, load a timeline JSON in Chromium at <code>chrome://tracing</code>.
A browser may show the raw JSON first; save it and load that file in the tracing viewer.
Viewer archives require a compatible NPU report viewer.</p>
<p>The numerical check and diagnostic detectors answer different questions. The detector results
and collection limitations below are preserved, including any violations.</p>'''
page += '\n'.join(sections) + '</html>\n'
(root / 'RESULTS.html').write_text(page)
print(root / 'RESULTS.html')
