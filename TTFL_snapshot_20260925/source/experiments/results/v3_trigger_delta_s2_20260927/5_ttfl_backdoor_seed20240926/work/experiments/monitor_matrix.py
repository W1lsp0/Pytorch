#!/usr/bin/env python3
"""Persist read-only monitoring snapshots without changing training or recovery."""
import argparse
import datetime
import json
import os
import re
import time
from pathlib import Path


def alive(pid_file):
    if not pid_file.exists():
        return False
    pid = int(pid_file.read_text())
    try:
        return not Path(f'/proc/{pid}/stat').read_text().split(') ', 1)[1].startswith('Z')
    except OSError:
        return False


def snapshot(matrix):
    config = json.loads((matrix/'resume_config.json').read_text())
    expected = len(config['METHOD_LIST'].split()) * len(config['SCENARIO_LIST'].split()) * len(config['SEED_LIST'].split())
    rows = []
    for path in sorted(matrix.glob('*/manifest.json'), key=lambda p:int(p.parent.name.split('_')[0])):
        run = path.parent
        log = run/'work/log/server.log'
        text = log.read_text(errors='replace') if log.exists() else ''
        counts = re.findall(r'aggregate_(fit|evaluate): received (\d+) results and (\d+) failures', text)
        manifest = json.loads(path.read_text())
        complete = json.loads((run/'completion.json').read_text()) if (run/'completion.json').exists() else {}
        rows.append(dict(run=run.name, status=complete.get('status', 'running'),
                         fit=sum(x[0]=='fit' for x in counts), evaluate=sum(x[0]=='evaluate' for x in counts),
                         unexpected_returns=[list(x) for x in counts if int(x[1])!=manifest['clients'] or int(x[2])!=0],
                         error=complete.get('error'), server_log_idle_seconds=round(time.time()-log.stat().st_mtime) if log.exists() else None))
    controller = alive(matrix/'controller.pid')
    watcher = alive(matrix/'watcher.pid')
    done = matrix/'watcher_done.json'
    verified = False
    if done.exists() and (matrix/'protocol_audit.json').exists():
        audit = json.loads((matrix/'protocol_audit.json').read_text())
        verified = (json.loads(done.read_text()).get('status') == 'complete' and len(rows)==expected
                    and all(r['status']=='success' for r in rows)
                    and audit['run_count']==expected and not audit['failed_runs'])
        if config.get('REPORT_KIND') == 'trigger_delta':
            report = matrix/'trigger_delta_report.json'
            verified = verified and report.exists() and json.loads(report.read_text()).get('complete') is True
    warnings = []
    for r in rows:
        if r['unexpected_returns']:
            warnings.append(f"{r['run']}: unexpected client results")
        if r['status']=='failure':
            warnings.append(f"{r['run']}: {r['error']}")
        if r['status']=='running' and (r['server_log_idle_seconds'] or 0)>900:
            warnings.append(f"{r['run']}: no server log update for over 15 minutes")
    if not verified and not controller and not watcher:
        warnings.append('controller and watcher both stopped before verified completion')
    return dict(checked_at=datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
                expected_runs=expected, created_runs=len(rows),
                successful_runs=sum(r['status']=='success' for r in rows),
                pending_runs=expected-len(rows), controller_alive=controller, watcher_alive=watcher,
                verified_complete=verified, warnings=warnings, runs=rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('matrix', type=Path)
    ap.add_argument('--once', action='store_true')
    args = ap.parse_args()
    matrix = args.matrix.resolve()
    if not matrix.is_relative_to(Path('/data1/lab409/W1lsp0')):
        raise ValueError('matrix must be under user root')
    previous = None
    while True:
        state = snapshot(matrix)
        temporary = matrix/'monitor_status.json.tmp'
        temporary.write_text(json.dumps(state,indent=2,ensure_ascii=False)+'\n')
        os.replace(temporary, matrix/'monitor_status.json')
        signature = (state['verified_complete'], state['warnings'],
                     [(r['run'],r['status'],r['fit'],r['evaluate']) for r in state['runs']])
        if signature != previous:
            with (matrix/'monitor_events.jsonl').open('a') as f:
                f.write(json.dumps(state,ensure_ascii=False)+'\n')
            print(json.dumps(dict(checked_at=state['checked_at'],successful=state['successful_runs'],
                                  pending=state['pending_runs'],verified_complete=state['verified_complete'],
                                  warnings=state['warnings'],
                                  progress=[(r['run'].split('_')[0],r['fit'],r['evaluate'],r['status']) for r in state['runs']]),ensure_ascii=False),flush=True)
            previous = signature
        if args.once or state['verified_complete']:
            break
        time.sleep(30)


if __name__ == '__main__':
    main()
