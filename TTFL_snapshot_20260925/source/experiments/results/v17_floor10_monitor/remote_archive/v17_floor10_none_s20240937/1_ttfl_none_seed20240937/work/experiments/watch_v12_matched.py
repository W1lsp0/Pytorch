#!/usr/bin/env python3
"""Persist V12 health checks, pull remote evidence, and refresh strict reports."""
import argparse
import fcntl
import json
from pathlib import Path
import subprocess
import sys
import time

from report_v12_matched import write_reports


def atomic(path, data):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, indent=2) + '\n')
    temp.replace(path)

def reminder(out, report):
    """Leave a durable handoff for the next assistant turn."""
    marker = Path('/data1/lab409/W1lsp0/EXPERIMENT_COMPLETE_REMINDER.json')
    marker.write_text(json.dumps({
        'batch': 'v12_matched', 'completed_at': time.time(),
        'report': str(out / 'matched_report.json'),
        'validation_complete': bool(report.get('complete')),
        'goal_achieved': False,
        'action': 'Read matched_report.json and continue optimization; do not treat batch completion as research success.'
    }, indent=2) + '\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('spec', type=Path)
    args = ap.parse_args()
    spec = json.loads(args.spec.read_text())
    out = args.spec.parent
    lock = (out / 'watcher.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    (out / 'watcher.pid').write_text(str(__import__('os').getpid()))
    ssh = ['ssh', '-i', '/data1/lab409/W1lsp0/ssh_config/id_rsa_spug', '-p', '2222',
           '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', 'user@59.67.152.228']
    remote = '/mnt/data/zjk/TTFL/results/v12_low_entropy_guard_seed20240933'
    last_sync = 0
    while True:
        errors = []
        health = dict(checked_at=time.time())
        try:
            path = Path(spec['local_monitor'])
            health['local'] = json.loads(path.read_text())
            response = subprocess.run(ssh + ['cat', remote + '/control/monitor_status.json'],
                            capture_output=True, text=True, timeout=25, check=True)
            health['remote'] = json.loads(response.stdout)
            for host in ('local', 'remote'):
                if time.time() - health[host]['checked_at'] > 120:
                    # Completed supervisors stop updating by design.
                    if not all(r['status'] in ('success', 'failure') for r in health[host]['runs']):
                        errors.append(host + ': stale supervisor heartbeat')
                errors.extend(host + ': ' + r['name'] + ': ' + warning
                              for r in health[host]['runs'] for warning in r['warnings'])
                errors.extend(host + ': ' + r['name'] + ': ' + r['status']
                              for r in health[host]['runs'] if r['status'] in ('failure', 'launcher_lost'))
        except Exception as exc:
            errors.append(str(exc))
        if time.time() - last_sync > 300:
            try:
                subprocess.run(['rsync', '-az', '--exclude=control/source/',
                    '-e', 'ssh -i /data1/lab409/W1lsp0/ssh_config/id_rsa_spug -p 2222 -o BatchMode=yes -o ConnectTimeout=10',
                    'user@59.67.152.228:' + remote + '/', spec['remote_archive'] + '/'],
                    capture_output=True, text=True, check=True, timeout=90)
                last_sync = time.time()
            except Exception as exc:
                errors.append('remote sync: ' + str(exc))
        try:
            result = write_reports(args.spec)
            health['report_complete'] = result['complete']
            errors.extend(p['name'] + ': ' + p.get('error', p['validation'])
                          for p in result['pairs'] if p['validation'] in ('audit_failed', 'failed_run'))
        except Exception as exc:
            errors.append('report: ' + str(exc))
        health['warnings'] = errors
        health['remote_last_sync'] = last_sync
        atomic(out / 'health.json', health)
        with (out / 'health_events.jsonl').open('a') as f:
            f.write(json.dumps(health) + '\n')
        if health.get('report_complete'):
            atomic(out / 'closeout.json', dict(status='paired_reports_complete', time=time.time(),
                   goal_achieved=False, note='Review matched_report.md; completion of runs is not success of the research objective.'))
            reminder(out, result)
            return
        time.sleep(30)


if __name__ == '__main__':
    main()
