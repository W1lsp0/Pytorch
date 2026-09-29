#!/usr/bin/env python3
"""Adopt existing V11 runs, then fill each released GPU from a frozen queue."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


def save(path, value):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, indent=2) + '\n')
    tmp.replace(path)


def processes_under(root):
    found = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            cwd = (proc / 'cwd').resolve(strict=True)
            if cwd.is_relative_to(root):
                found.append(int(proc.name))
        except (OSError, RuntimeError):
            pass
    return found


def inspect(matrix):
    runs = sorted(matrix.glob('*/manifest.json'))
    if not runs:
        return dict(status='absent', fit=0, evaluate=0, warnings=[])
    if len(runs) != 1:
        raise RuntimeError(f'expected one run: {matrix}')
    run = runs[0].parent
    completion = run / 'completion.json'
    state = json.loads(completion.read_text()).get('status') if completion.exists() else 'running'
    log = run / 'work/log/server.log'
    content = log.read_text(errors='replace') if log.exists() else ''
    counts = re.findall(r'aggregate_(fit|evaluate): received (\d+) results and (\d+) failures', content)
    warnings = []
    if any(int(n) != 20 or int(f) != 0 for _, n, f in counts):
        warnings.append('unexpected client results')
    if state == 'running' and log.exists() and time.time() - log.stat().st_mtime > 900:
        warnings.append('server log idle > 900 seconds')
    return dict(status=state, fit=sum(p == 'fit' for p, _, _ in counts),
                evaluate=sum(p == 'evaluate' for p, _, _ in counts), warnings=warnings)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('plan', type=Path)
    args = ap.parse_args()
    plan = json.loads(args.plan.read_text())
    root = Path(plan['result_root'])
    control = root / 'control'
    control.mkdir(exist_ok=True)
    lock = (control / 'supervisor.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    (control / 'supervisor.pid').write_text(str(os.getpid()))
    children = {}
    while True:
        memory = subprocess.check_output(['nvidia-smi', '--query-gpu=index,memory.used',
                    '--format=csv,noheader,nounits'], text=True)
        gpu_memory = {i.strip(): int(m.strip()) for i, m in (line.split(',') for line in memory.splitlines())}
        states = []
        for gpu, jobs in plan['slots'].items():
            slot_busy = False
            for job in jobs:
                matrix = root / job['name']
                state = inspect(matrix)
                state.update(name=job['name'], gpu=gpu, adopted=job.get('adopt', False))
                child = children.get(job['name'])
                if child is not None and child.poll() is not None and state['status'] not in ('success', 'failure'):
                    state['status'] = 'launcher_lost'
                    state['warnings'].append(f'matrix exited {child.returncode} without completion')
                states.append(state)
                if slot_busy:
                    continue
                if state['status'] in ('success', 'failure'):
                    if processes_under(matrix):
                        slot_busy = True
                    if child is not None and child.poll() is None:
                        slot_busy = True
                    continue
                slot_busy = True
                if child is not None and child.poll() is None:
                    continue
                if state['status'] != 'absent' or job.get('adopt'):
                    continue
                # Respect unrelated workloads on this shared server.
                if gpu_memory[gpu] > 500:
                    state['warnings'].append('waiting for GPU memory to be released')
                    continue
                env = dict(os.environ, **plan['environment'], **job['environment'],
                           GPU_VISIBLE_LIST=gpu, RESULT_ROOT=str(matrix))
                log = (root / 'logs' / (job['name'] + '.queue.log')).open('a')
                child = subprocess.Popen([sys.executable, str(Path(plan['source']) / 'experiments/run_parallel_matrix.py')],
                            cwd=plan['source'], env=env, stdout=log, stderr=subprocess.STDOUT,
                            stdin=subprocess.DEVNULL, start_new_session=True)
                log.close()
                children[job['name']] = child
                state.update(status='starting', pid=child.pid)
                save(control / (job['name'] + '.launch.json'), dict(pid=child.pid, time=time.time(),
                     environment=dict(plan['environment'], **job['environment'], GPU_VISIBLE_LIST=gpu, RESULT_ROOT=str(matrix))))
        result = dict(checked_at=time.time(), host=plan['host'], gpu_memory_mib=gpu_memory, runs=states)
        save(control / 'monitor_status.json', result)
        with (control / 'monitor_events.jsonl').open('a') as f:
            f.write(json.dumps(result) + '\n')
        if all(s['status'] in ('success', 'failure') for s in states) and all(p.poll() is not None for p in children.values()):
            save(control / 'queue_done.json', dict(time=time.time(), success=all(s['status'] == 'success' for s in states)))
            return
        time.sleep(30)


if __name__ == '__main__':
    main()
