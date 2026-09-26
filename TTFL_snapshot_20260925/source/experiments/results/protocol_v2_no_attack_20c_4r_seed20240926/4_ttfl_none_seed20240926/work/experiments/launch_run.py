#!/usr/bin/env python3
"""Launch one Flower job; supervise only owned processes, fail on child errors."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def gpu_devices():
    visible = os.getenv('CUDA_VISIBLE_DEVICES')
    if visible is not None:
        return [v for v in visible.split(',') if v and v != '-1']
    result = subprocess.run(['nvidia-smi', '--query-gpu=index', '--format=csv,noheader'],
                            capture_output=True, text=True, check=True)
    return result.stdout.split()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    count = int(os.getenv('TOTAL_CLIENTS', '20'))
    if not 4 <= count <= 20:
        raise ValueError('hybrid protocol requires 4..20 clients')
    devices = gpu_devices()
    offset = int(os.getenv('GPU_OFFSET', '0'))
    assignments = [devices[(i + offset) % len(devices)] if devices else '' for i in range(count)]
    server_gpu = devices[offset % len(devices)] if devices else ''
    profile = os.getenv('ATTACK_PROFILE', 'none')
    if profile not in ('none', 'backdoor', 'mixed'):
        raise ValueError(f'unknown attack profile: {profile}')
    schedule = {i: ('none', '0') for i in range(count)}
    if profile == 'backdoor':
        schedule[1] = ('backdoor', os.getenv('BACKDOOR_POISON_RATE', '0.2'))
    elif profile == 'mixed':
        schedule.update({0: ('label_flip', '0.5'), 1: ('backdoor', '0.2'),
                         2: ('clean_label', '0.5'), 3: ('semantic', '0.5')})
    mapping = dict(server=server_gpu, clients=assignments)
    print(json.dumps(mapping), flush=True)
    if args.dry_run or os.getenv('DRY_RUN') == '1':
        return
    logs = root / 'log'
    logs.mkdir(exist_ok=True)
    if (logs / 'server.log').exists():
        raise RuntimeError('log/server.log exists; use a fresh isolated work directory')
    (logs / 'gpu_mapping.json').write_text(json.dumps(mapping, indent=2))
    env = os.environ.copy()
    for key, value in {'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1',
                       'TTFL_DISABLE_DB': '1', 'USE_SIMULATION': '0',
                       'PYTHONUNBUFFERED': '1', 'GRPC_ENABLE_FORK_SUPPORT': '0'}.items():
        env[key] = value
    python = os.getenv('PYTHON_BIN', sys.executable)
    owned = []
    handles = []
    def stop(signum, frame):
        raise InterruptedError(f'interrupted by signal {signum}')
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    def launch(name, cmd, settings):
        handle = (logs / f'{name}.log').open('w')
        handles.append(handle)
        proc = subprocess.Popen([python, *cmd], cwd=root, env=dict(env, **settings),
                                stdout=handle, stderr=subprocess.STDOUT, start_new_session=True)
        owned.append((name, proc))
    try:
        launch('server', ['server/server.py', '--server_address=' + env.get('SERVER_ADDRESS', '127.0.0.1:8080')],
               {'CUDA_VISIBLE_DEVICES': server_gpu})
        # Clients retry the gRPC connection while the server initializes.
        for i, gpu in enumerate(assignments):
            attack, rate = schedule[i]
            launch(f'client_{i}', ['Client/client.py'], {'CUDA_VISIBLE_DEVICES': gpu,
                   'CLIENT_ID': str(i), 'ATTACK_TYPE': attack, 'POISON_RATE': rate, 'TARGET_LABEL': '0'})
        deadline = time.monotonic() + int(env.get('RUN_TIMEOUT_SECONDS', '7200'))
        server_finished_at = None
        while True:
            states = [(name, proc.poll()) for name, proc in owned]
            bad = [(name, code) for name, code in states if code not in (None, 0)]
            if bad:
                raise RuntimeError(f'child process failed: {bad}')
            if all(code == 0 for _, code in states):
                break
            if states[0][1] == 0:
                server_finished_at = server_finished_at or time.monotonic()
                if time.monotonic() - server_finished_at > 30:
                    raise RuntimeError('clients did not exit after server completed')
            if time.monotonic() > deadline:
                raise TimeoutError('experiment exceeded RUN_TIMEOUT_SECONDS')
            time.sleep(0.5)
    finally:
        alive = [proc for _, proc in owned if proc.poll() is None]
        for proc in alive:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        for proc in alive:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
        for handle in handles:
            handle.close()


if __name__ == '__main__':
    main()
