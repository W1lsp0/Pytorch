#!/usr/bin/env python3
"""Launch one Flower job; supervise only owned processes, fail on child errors."""
import argparse
import hashlib
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
    allowed_root = Path(os.getenv('TTFL_ALLOWED_ROOT', '/data1/lab409/W1lsp0')).resolve()
    if not root.resolve().is_relative_to(allowed_root):
        raise RuntimeError(f'run root must be under {allowed_root}: {root}')
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
    # Use a short path for multiprocessing IPC sockets. The matrix launcher
    # supplies a per-run directory under the user's allowed root.
    short_id = hashlib.sha256(str(root).encode()).hexdigest()[:12]
    local_tmp = Path(os.getenv('TTFL_TMP_ROOT', str(allowed_root / '.ttfl_tmp' / short_id))).resolve()
    if not local_tmp.is_relative_to(allowed_root) or len(os.fsencode(local_tmp)) > 70:
        raise ValueError('temporary directory must be under the allowed root and at most 70 bytes long')
    local_tmp.mkdir(parents=True, exist_ok=True)
    if (logs / 'server.log').exists():
        raise RuntimeError('log/server.log exists; use a fresh isolated work directory')
    (logs / 'gpu_mapping.json').write_text(json.dumps(mapping, indent=2))
    env = os.environ.copy()
    for key, value in {'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1',
                       'TTFL_DISABLE_DB': '1', 'USE_SIMULATION': '0',
                       'PYTHONUNBUFFERED': '1', 'GRPC_ENABLE_FORK_SUPPORT': '0',
                       'TMPDIR': str(local_tmp), 'TEMP': str(local_tmp), 'TMP': str(local_tmp)}.items():
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
        startup_delay = float(env.get('CLIENT_START_DELAY', '0'))
        if startup_delay > 0:
            time.sleep(startup_delay)
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
                    # Flower's server has already written the complete round
                    # history. Some clients keep their gRPC/DataLoader loop
                    # alive after the server closes; end those owned groups
                    # cleanly and treat the protocol as complete.
                    for _, client_proc in owned[1:]:
                        if client_proc.poll() is None:
                            try:
                                os.killpg(client_proc.pid, signal.SIGTERM)
                            except ProcessLookupError:
                                pass
                    for _, client_proc in owned[1:]:
                        try:
                            client_proc.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            pass
                    if all(proc.poll() in (0, -signal.SIGTERM, -signal.SIGKILL) for _, proc in owned[1:]):
                        break
                    raise RuntimeError('clients did not exit after server completion')
            if time.monotonic() > deadline:
                raise TimeoutError('experiment exceeded RUN_TIMEOUT_SECONDS')
            time.sleep(0.5)
    finally:
        # A second interrupt must not abort cleanup. Signal all owned groups,
        # including groups whose leader exited but left DataLoader workers.
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        for _, proc in owned:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        cleanup_deadline = time.monotonic() + 5
        for _, proc in owned:
            try:
                proc.wait(timeout=max(0, cleanup_deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                pass
        for _, proc in owned:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait()
        for handle in handles:
            handle.close()


if __name__ == '__main__':
    main()
