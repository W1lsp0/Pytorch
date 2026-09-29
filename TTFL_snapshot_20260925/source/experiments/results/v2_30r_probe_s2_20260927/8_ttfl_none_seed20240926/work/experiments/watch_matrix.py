#!/usr/bin/env python3
"""Finish archiving orphaned complete runs, then resume the remaining jobs."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = Path('/data1/lab409/W1lsp0').resolve()


def active_processes(matrix):
    """Match owned run cwd or the controller's explicit RESULT_ROOT env."""
    found = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit() or int(proc.name) == os.getpid():
            continue
        try:
            if proc.stat().st_uid != os.getuid():
                continue
            # Zombies no longer own GPU resources or write logs.
            if (proc/'stat').read_text().split(') ', 1)[1].startswith('Z'):
                continue
            cwd = (proc/'cwd').resolve()
            cmd = (proc/'cmdline').read_bytes().split(b'\0')
            if cwd.is_relative_to(matrix) and b'experiments/launch_run.py' in cmd:
                found.append(int(proc.name))
            elif cwd.is_relative_to(matrix) and any(x in cmd for x in (b'server/server.py', b'Client/client.py')):
                found.append(int(proc.name))
            elif b'experiments/run_parallel_matrix.py' in cmd:
                env = dict(x.split(b'=', 1) for x in (proc/'environ').read_bytes().split(b'\0') if b'=' in x)
                if env.get(b'RESULT_ROOT') == str(matrix).encode():
                    found.append(int(proc.name))
        except (OSError, ValueError):
            continue
    return found


def archive_orphan(run):
    manifest = json.loads((run/'manifest.json').read_text())
    completion = run/'completion.json'
    if completion.exists():
        if json.loads(completion.read_text()).get('status') != 'success':
            raise RuntimeError(f'failed run requires review: {run}')
        return
    logs = run/'work/log'
    text = (logs/'server.log').read_text(errors='replace')
    for phase in ('fit', 'evaluate'):
        counts = re.findall(r'aggregate_' + phase + r': received (\d+) results and (\d+) failures', text)
        if len(counts) != manifest['rounds'] or any(int(n) != manifest['clients'] or int(f) for n, f in counts):
            raise RuntimeError(f'incomplete orphan, refusing to overwrite: {run}')
    subprocess.run([sys.executable, str(ROOT/'experiments/analyze_run.py'), str(logs)], check=True)
    for item in logs.iterdir():
        if item.is_dir():
            shutil.copytree(item, run/item.name, dirs_exist_ok=True)
        else:
            shutil.copy2(item, run/item.name)
    completion.write_text(json.dumps(dict(status='success', recovered_after_parent_exit=True,
        child_exit_codes_available=False, validation='all fit/evaluate rounds complete with zero failures'), indent=2))
    (run/'status').write_text('success\n')
    print(f'Recovered {run.name} from complete logs', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config', type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    matrix = Path(config['RESULT_ROOT']).resolve()
    if not matrix.is_relative_to(ALLOWED):
        raise ValueError('matrix outside allowed root')
    with (matrix/'watcher.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        print('Watching existing controller and owned children', flush=True)
        while active_processes(matrix):
            time.sleep(30)
        for manifest in matrix.glob('*/manifest.json'):
            archive_orphan(manifest.parent)
        env = dict(os.environ, **config)
        # Popen detached from the interactive tool session; output stays local.
        with (matrix/'resumed_controller.log').open('a') as log:
            subprocess.run([sys.executable, 'experiments/run_parallel_matrix.py'], cwd=ROOT,
                           env=env, stdout=log, stderr=subprocess.STDOUT, check=True,
                           start_new_session=True)
        subprocess.run([sys.executable, str(ROOT/'experiments/protocol_audit.py'), str(matrix)], check=True)
        expected_runs = len(config['METHOD_LIST'].split()) * len(config['SEED_LIST'].split()) * len(config['SCENARIO_LIST'].split())
        audit = json.loads((matrix/'protocol_audit.json').read_text())
        if audit['run_count'] != expected_runs:
            raise RuntimeError(f'expected {expected_runs} runs, found {audit["run_count"]}')
        if config['SCENARIO_LIST'] == 'recovery_backdoor':
            subprocess.run([sys.executable, str(ROOT/'experiments/report_recovery.py'), str(matrix)], check=True)
        if config.get('REPORT_KIND') == 'probe':
            subprocess.run([sys.executable, str(ROOT/'experiments/report_probe_matrix.py'), str(matrix)], check=True)
        (matrix/'watcher_done.json').write_text(json.dumps(dict(status='complete', completed_at=time.time())))
        print('Matrix complete and audited', flush=True)


if __name__ == '__main__':
    main()
