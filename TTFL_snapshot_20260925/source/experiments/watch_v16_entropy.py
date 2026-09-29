#!/usr/bin/env python3
"""Monitor V16 queues and synchronize evidence without touching training jobs."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import time
from report_v16_entropy import write_reports, screen
from supervise_v11_node import save

ROOT = Path(__file__).resolve().parent / 'results/v16_entropy_monitor'
SSH = ['ssh', '-i', '/data1/lab409/W1lsp0/ssh_config/id_rsa_spug',
       '-p', '2222', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
       'user@59.67.152.228']

def main():
    lock = (ROOT / 'watcher.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    (ROOT / 'watcher.pid').write_text(str(os.getpid()))
    plans = {h: json.loads((ROOT / f'{h}_plan.json').read_text()) for h in ('local', 'remote')}
    last_sync = 0
    terminal_synced = False
    while True:
        health = {'checked_at': time.time(), 'warnings': []}
        for host, plan in plans.items():
            try:
                path = plan['result_root'] + '/control/monitor_status.json'
                raw = Path(path).read_text() if host == 'local' else subprocess.check_output(SSH + ['cat ' + path], text=True, timeout=30)
                state = json.loads(raw)
                health[host] = state
                health['warnings'].extend(host + ': ' + w for w in state.get('warnings', []))
                if any(r['status'] not in ('success', 'failure') for r in state['runs']) and time.time() - state['checked_at'] > 120:
                    health['warnings'].append(host + ': queue heartbeat stale >120s')
            except Exception as exc:
                health['warnings'].append(host + ': ' + str(exc))
        remote_runs = health.get('remote', {}).get('runs', [])
        terminal = bool(remote_runs) and all(r['status'] in ('success', 'failure') for r in remote_runs)
        if time.time() - last_sync >= 300 or (terminal and not terminal_synced):
            try:
                subprocess.run(['rsync', '-az', '--exclude=control/', '-e',
                    'ssh -i /data1/lab409/W1lsp0/ssh_config/id_rsa_spug -p 2222 -o BatchMode=yes -o ConnectTimeout=10',
                    'user@59.67.152.228:' + plans['remote']['result_root'] + '/', str(ROOT / 'remote_archive') + '/'],
                    capture_output=True, text=True, check=True, timeout=90)
                last_sync = time.time()
                terminal_synced = terminal
            except Exception as exc:
                health['warnings'].append('remote sync: ' + str(exc))
        health['remote_last_sync'] = last_sync
        try:
            report = write_reports(ROOT / 'pairs.json')
            decision = screen(report)
            save(ROOT / 'decision.json', decision)
            health['report_complete'] = report['complete']
        except Exception as exc:
            health['warnings'].append('report: ' + str(exc))
            health['report_complete'] = False
        save(ROOT / 'health.json', health)
        if health['report_complete']:
            event = {'batch': 'v16_entropy', 'completed_at': time.time(),
                     'validation_complete': True, 'goal_achieved': decision['goal_achieved'], 'decision': decision}
            save(ROOT / 'closeout.json', event)
            save(Path('/data1/lab409/W1lsp0/EXPERIMENT_COMPLETE_REMINDER.json'), event)
            return
        time.sleep(30)

if __name__ == '__main__':
    main()
