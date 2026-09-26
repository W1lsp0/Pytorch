#!/usr/bin/env python3
"""Bounded concurrent experiments with immutable code copies and shared data."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
STOP = threading.Event()


def snapshot(work):
    work.mkdir(parents=True, exist_ok=False)
    # Copy only executable sources, never hard-link mutable logs or code.
    for directory in ('Client', 'server'):
        shutil.copytree(ROOT / directory, work / directory,
                        ignore=shutil.ignore_patterns('__pycache__', '*.log'))
    (work / 'experiments').mkdir()
    for path in (ROOT / 'experiments').glob('*.py'):
        shutil.copy2(path, work / 'experiments' / path.name)
    for path in ROOT.glob('*.py'):
        shutil.copy2(path, work / path.name)
    (work / 'data').symlink_to(ROOT / 'data', target_is_directory=True)
    digest = hashlib.sha256()
    for path in sorted(work.rglob('*.py')):
        digest.update(str(path.relative_to(work)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def run_one(job):
    run_dir, method, scenario, seed, port, index, params = job
    run_dir.mkdir(parents=True, exist_ok=False)
    status_path = run_dir / 'status'
    status_path.write_text('running\n')
    work = run_dir / 'work'
    started = time.time()
    outcome = {'status': 'failure', 'started_at': started}
    try:
        code_hash = snapshot(work)
        env = os.environ.copy()
        profile = 'none' if scenario == 'none' else 'backdoor'
        attack_start = params['attack_start'] if scenario == 'delayed_backdoor' else 1
        env.update(PYTHON_BIN=sys.executable, TOTAL_CLIENTS=str(params['clients']),
                   NUM_ROUNDS=str(params['rounds']), LOCAL_EPOCHS=str(params['epochs']),
                   EXPERIMENT_SEED=str(seed), ATTACK_PROFILE=profile,
                   ATTACK_START_ROUND=str(attack_start), ATTACK_STOP_ROUND=str(params['attack_stop']),
                   BACKDOOR_POISON_RATE=str(params['poison_rate']), AGGREGATION_MODE=method,
                   TTFL_DOWNLOAD_DATA='0', USE_PRETRAINED_MODEL='0', SHARED_CLIENT_POOL_SIZE='0',
                   SERVER_PROXY_SIZE='500', ENABLE_KNOWN_TRIGGER_PROBE=str(params['known_probe']),
                   HEAVY_PROBE_ROTATE_MOD=str(params['probe_rotate']), ENABLE_PCA_PANEL='0',
                   USE_CLIENT_REPORT_FOR_DECISIONS='0', TTFL_DISABLE_DB='1', USE_SIMULATION='0',
                   CUDA_VISIBLE_DEVICES=params['gpus'], GPU_OFFSET=str(index),
                   SERVER_ADDRESS=f'127.0.0.1:{port}', RUN_TIMEOUT_SECONDS=str(params['timeout']),
                   OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1')
        manifest = dict(protocol_version=2, method=method, scenario=scenario, seed=seed,
                        clients=params['clients'], rounds=params['rounds'], local_epochs=params['epochs'],
                        attack_start_round=attack_start, attack_stop_round=params['attack_stop'],
                        malicious_client_ids=[] if profile == 'none' else [1],
                        poison_rate=params['poison_rate'], dataset='CIFAR10_LOCAL',
                        shared_client_pool_size=0, server_proxy_size=500,
                        known_trigger_probe=bool(params['known_probe']), heavy_probe_rotate_mod=params['probe_rotate'],
                        asr_excludes_target_label=True, code_sha256=code_hash,
                        python=sys.executable, server_address=env['SERVER_ADDRESS'],
                        gpu_visible_list=params['gpus'])
        (run_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2))
        aliases = dict(METHOD=method, SCENARIO=scenario, SEED=seed, CLIENTS=params['clients'],
                       ROUNDS=params['rounds'], LOCAL_EPOCHS=params['epochs'], ATTACK_START_ROUND=attack_start,
                       ATTACK_STOP_ROUND=params['attack_stop'], BACKDOOR_POISON_RATE=params['poison_rate'])
        (run_dir / 'manifest.env').write_text(''.join(f'{k}={v}\n' for k,v in aliases.items()))
        print(f'[start] {run_dir.name} port={port} GPUs={params["gpus"]}', flush=True)
        with (run_dir / 'launcher.log').open('w') as log:
            process = subprocess.Popen([sys.executable, 'experiments/launch_run.py'], cwd=work,
                                       env=env, stdout=log, stderr=subprocess.STDOUT)
            while process.poll() is None:
                if STOP.wait(1):
                    process.terminate()
                    process.wait(timeout=150)
                    raise InterruptedError('matrix interrupted')
        if process.returncode:
            raise RuntimeError(f'launcher exited {process.returncode}')
        # Validate the finished run, including all rounds and all expected clients.
        subprocess.run([sys.executable, str(ROOT/'experiments/analyze_run.py'), str(work/'log')],
                       stdout=subprocess.DEVNULL, check=True)
        outcome['status'] = 'success'
    except Exception as exc:
        outcome['error'] = str(exc)
    finally:
        logs = work / 'log'
        if logs.exists():
            for item in logs.iterdir():
                if item.is_dir():
                    shutil.copytree(item, run_dir/item.name, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, run_dir/item.name)
        outcome['elapsed_seconds'] = time.time() - started
        (run_dir/'completion.json').write_text(json.dumps(outcome, indent=2))
        status_path.write_text(outcome['status']+'\n')
        print(f'[{outcome["status"]}] {run_dir.name}: {outcome.get("error", "validated")}', flush=True)
    return outcome['status'] == 'success'


def main():
    params = dict(clients=int(os.getenv('CLIENTS','20')), rounds=int(os.getenv('ROUNDS','4')),
                  epochs=int(os.getenv('LOCAL_EPOCHS','1')), attack_start=int(os.getenv('ATTACK_START_ROUND','3')),
                  attack_stop=int(os.getenv('ATTACK_STOP_ROUND','0')), poison_rate=float(os.getenv('BACKDOOR_POISON_RATE','0.2')),
                  known_probe=int(os.getenv('KNOWN_TRIGGER_PROBE','0')), probe_rotate=int(os.getenv('HEAVY_PROBE_ROTATE_MOD','5')),
                  timeout=int(os.getenv('RUN_TIMEOUT_SECONDS','7200')), gpus=os.getenv('GPU_VISIBLE_LIST','0,1,2,3,4'))
    methods = os.getenv('METHOD_LIST','fedavg fltrust single_stream ttfl').split()
    scenarios = os.getenv('SCENARIO_LIST','none').split()
    if not set(methods) <= {'fedavg','fltrust','single_stream','ttfl'}:
        raise ValueError('invalid methods')
    if not set(scenarios) <= {'none','backdoor','delayed_backdoor'}:
        raise ValueError('invalid scenarios')
    # Validate real CIFAR before launching GPU processes.
    from torchvision.datasets import CIFAR10
    for train in (True, False):
        CIFAR10(str(ROOT/'data'), train=train, download=False)
    result_root = Path(os.getenv('RESULT_ROOT', str(ROOT/'experiments/results'/time.strftime('parallel_%Y%m%d_%H%M%S')))).resolve()
    seeds = [int(x) for x in os.getenv('SEED_LIST','20240925').split()]
    base = int(os.getenv('PORT_BASE','19600'))
    jobs = []
    for seed in seeds:
        for scenario in scenarios:
            for method in methods:
                index = len(jobs)
                run_dir = result_root/f'{index+1}_{method}_{scenario}_seed{seed}'
                if run_dir.exists():
                    raise FileExistsError(f'refusing to overwrite {run_dir}')
                jobs.append((run_dir, method, scenario, seed, base+index+1, index, params))
    signal.signal(signal.SIGTERM, lambda *_: STOP.set())
    signal.signal(signal.SIGINT, lambda *_: STOP.set())
    with ThreadPoolExecutor(max_workers=int(os.getenv('MAX_PARALLEL','4'))) as pool:
        results = list(pool.map(run_one, jobs))
    subprocess.run([sys.executable, str(ROOT/'experiments/summarize_matrix.py'), str(result_root)], check=True)
    return 0 if all(results) else 1


if __name__ == '__main__':
    sys.exit(main())
