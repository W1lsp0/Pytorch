#!/usr/bin/env python3
"""Bounded concurrent experiments with immutable code copies and shared data."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_ROOT = Path('/data1/lab409/W1lsp0').resolve()
STOP = threading.Event()

if not ROOT.resolve().is_relative_to(ALLOWED_ROOT):
    raise RuntimeError(f'source root must be under {ALLOWED_ROOT}: {ROOT}')


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
    if STOP.is_set():
        return False
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
        attack_start = params['attack_start'] if scenario in ('delayed_backdoor', 'recovery_backdoor') else 1
        tmp_root = Path(os.getenv('TTFL_SHARED_TMP_ROOT', str(ALLOWED_ROOT / '.ttfl_tmp')))
        # Unique across matrices, with room for multiprocessing socket suffixes.
        short_id = hashlib.sha256(str(run_dir.resolve()).encode()).hexdigest()[:12]
        local_tmp = (tmp_root / short_id).resolve()
        if not local_tmp.is_relative_to(ALLOWED_ROOT) or len(os.fsencode(local_tmp)) > 70:
            raise ValueError('temporary directory must be under the allowed root and at most 70 bytes long')
        local_tmp.mkdir(parents=True, exist_ok=True)
        env.update(PYTHON_BIN=sys.executable, TOTAL_CLIENTS=str(params['clients']),
                   NUM_ROUNDS=str(params['rounds']), LOCAL_EPOCHS=str(params['epochs']),
                   EXPERIMENT_SEED=str(seed), ATTACK_PROFILE=profile,
                   ATTACK_START_ROUND=str(attack_start), ATTACK_STOP_ROUND=str(params['attack_stop']),
                   BACKDOOR_POISON_RATE=str(params['poison_rate']), AGGREGATION_MODE=method,
                   TTFL_DOWNLOAD_DATA='0', USE_PRETRAINED_MODEL='0', SHARED_CLIENT_POOL_SIZE='0',
                   SERVER_PROXY_SIZE='500', ENABLE_KNOWN_TRIGGER_PROBE=str(params['known_probe']),
                   HEAVY_PROBE_ROTATE_MOD=str(params['probe_rotate']), ENABLE_PCA_PANEL='0',
                   TRIGGER_SCORE_MODE=params['trigger_score_mode'],
                   RISK_RAW_ATTENUATION_POWER=str(params['risk_raw_attenuation_power']),
                   RISK_CROSS_CHANNEL_GUARD=str(params['risk_cross_channel_guard']),
                   RISK_SOFT_PROBATION=str(params.get('risk_soft_probation', 0)),
                   USE_CLIENT_REPORT_FOR_DECISIONS='0', TTFL_DISABLE_DB='1', USE_SIMULATION='0',
                   CUDA_VISIBLE_DEVICES=params['gpus'], GPU_OFFSET=str(index),
                   SERVER_ADDRESS=f'127.0.0.1:{port}', RUN_TIMEOUT_SECONDS=str(params['timeout']),
                   OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                   TMPDIR=str(local_tmp), TEMP=str(local_tmp), TMP=str(local_tmp),
                   TTFL_TMP_ROOT=str(local_tmp))
        manifest = dict(protocol_version=2, method=method, scenario=scenario, seed=seed,
                        clients=params['clients'], rounds=params['rounds'], local_epochs=params['epochs'],
                        attack_start_round=attack_start, attack_stop_round=params['attack_stop'],
                        malicious_client_ids=[] if profile == 'none' else [1],
                        poison_rate=params['poison_rate'], dataset='CIFAR10_LOCAL',
                        shared_client_pool_size=0, server_proxy_size=500,
                        known_trigger_probe=bool(params['known_probe']), heavy_probe_rotate_mod=params['probe_rotate'],
                        trigger_score_mode=params['trigger_score_mode'],
                        risk_raw_attenuation_power=params['risk_raw_attenuation_power'],
                        risk_cross_channel_guard=bool(params['risk_cross_channel_guard']),
                        risk_soft_probation=bool(params.get('risk_soft_probation', 0)),
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
                                       env=env, stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True)
            while process.poll() is None:
                if STOP.wait(1):
                    process.terminate()
                    process.wait(timeout=150)
                    raise InterruptedError('matrix interrupted')
        if process.returncode:
            raise RuntimeError(f'launcher exited {process.returncode}')
        # Validate the finished run, including all rounds and all expected clients.
        server_text = (work / 'log/server.log').read_text(errors='replace')
        fit = re.findall(r'aggregate_fit: received (\d+) results and (\d+) failures', server_text)
        if len(fit) != params['rounds'] or any(int(n) != params['clients'] or int(f) != 0 for n, f in fit):
            raise RuntimeError(f'incomplete fit history: {fit}')
        evaluation = re.findall(r'aggregate_evaluate: received (\d+) results and (\d+) failures', server_text)
        if len(evaluation) != params['rounds'] or any(int(n) != params['clients'] or int(f) != 0 for n, f in evaluation):
            raise RuntimeError(f'incomplete evaluation history: {evaluation}')
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
    argparse.ArgumentParser(description=__doc__ + ' Configuration is supplied via environment variables.').parse_args()
    params = dict(clients=int(os.getenv('CLIENTS','20')), rounds=int(os.getenv('ROUNDS','4')),
                  epochs=int(os.getenv('LOCAL_EPOCHS','1')), attack_start=int(os.getenv('ATTACK_START_ROUND','3')),
                  attack_stop=int(os.getenv('ATTACK_STOP_ROUND','0')), poison_rate=float(os.getenv('BACKDOOR_POISON_RATE','0.2')),
                  known_probe=int(os.getenv('KNOWN_TRIGGER_PROBE','0')), probe_rotate=int(os.getenv('HEAVY_PROBE_ROTATE_MOD','5')),
                  trigger_score_mode=os.getenv('TRIGGER_SCORE_MODE', 'legacy'),
                  risk_raw_attenuation_power=float(os.getenv('RISK_RAW_ATTENUATION_POWER', '1.0')),
                  risk_cross_channel_guard=int(os.getenv('RISK_CROSS_CHANNEL_GUARD', '0')),
                  risk_soft_probation=int(os.getenv('RISK_SOFT_PROBATION', '0')),
                  timeout=int(os.getenv('RUN_TIMEOUT_SECONDS','7200')), gpus=os.getenv('GPU_VISIBLE_LIST','0,1,2,3,4'))
    methods = os.getenv('METHOD_LIST','fedavg fltrust single_stream ttfl').split()
    if params['trigger_score_mode'] not in ('legacy', 'clean_delta'):
        raise ValueError('invalid TRIGGER_SCORE_MODE')
    if params['trigger_score_mode'] == 'clean_delta' and not params['known_probe']:
        raise ValueError('clean_delta requires known trigger probe')
    if params['risk_raw_attenuation_power'] < 0:
        raise ValueError('risk attenuation power must be non-negative')
    scenarios = os.getenv('SCENARIO_LIST','none').split()
    if not set(methods) <= {'fedavg','fltrust','single_stream','ttfl'}:
        raise ValueError('invalid methods')
    if not set(scenarios) <= {'none','backdoor','delayed_backdoor','recovery_backdoor'}:
        raise ValueError('invalid scenarios')
    if 'recovery_backdoor' in scenarios and not 1 <= params['attack_start'] < params['attack_stop'] <= params['rounds']:
        raise ValueError('recovery requires 1 <= start < stop <= rounds; stop is exclusive')
    # Validate real CIFAR before launching GPU processes.
    from torchvision.datasets import CIFAR10
    for train in (True, False):
        CIFAR10(str(ROOT/'data'), train=train, download=False)
    result_root = Path(os.getenv('RESULT_ROOT', str(ROOT/'experiments/results'/time.strftime('parallel_%Y%m%d_%H%M%S')))).resolve()
    if not result_root.is_relative_to(ALLOWED_ROOT):
        raise ValueError(f'RESULT_ROOT must be under {ALLOWED_ROOT}: {result_root}')
    result_root.mkdir(parents=True, exist_ok=True)
    seeds = [int(x) for x in os.getenv('SEED_LIST','20240925').split()]
    base = int(os.getenv('PORT_BASE','19600'))
    jobs = []
    job_index = 0
    for seed in seeds:
        for scenario in scenarios:
            for method in methods:
                index = job_index
                job_index += 1
                run_dir = result_root/f'{index+1}_{method}_{scenario}_seed{seed}'
                if run_dir.exists():
                    completion = run_dir / 'completion.json'
                    status = (run_dir / 'status').read_text().strip() if (run_dir / 'status').exists() else ''
                    if status == 'success' and completion.exists():
                        saved = json.loads((run_dir/'manifest.json').read_text())
                        expected = dict(method=method, scenario=scenario, seed=seed,
                                        clients=params['clients'], rounds=params['rounds'],
                                        local_epochs=params['epochs'], poison_rate=params['poison_rate'],
                                        attack_start_round=params['attack_start'] if scenario in ('delayed_backdoor','recovery_backdoor') else 1,
                                        attack_stop_round=params['attack_stop'],
                                        known_trigger_probe=bool(params['known_probe']), heavy_probe_rotate_mod=params['probe_rotate'])
                        mismatched = [key for key,value in expected.items() if saved.get(key) != value]
                        if saved.get('trigger_score_mode', 'legacy') != params['trigger_score_mode']:
                            mismatched.append('trigger_score_mode')
                        if float(saved.get('risk_raw_attenuation_power', 1.0)) != params['risk_raw_attenuation_power']:
                            mismatched.append('risk_raw_attenuation_power')
                        if bool(saved.get('risk_cross_channel_guard', False)) != bool(params['risk_cross_channel_guard']):
                            mismatched.append('risk_cross_channel_guard')
                        if bool(saved.get('risk_soft_probation', False)) != bool(params['risk_soft_probation']):
                            mismatched.append('risk_soft_probation')
                        if mismatched or json.loads(completion.read_text()).get('status') != 'success':
                            raise ValueError(f'resume configuration mismatch for {run_dir}: {mismatched}')
                        print(f'[skip] {run_dir.name}: already successful', flush=True)
                        continue
                    raise FileExistsError(f'refusing to overwrite incomplete {run_dir}')
                jobs.append((run_dir, method, scenario, seed, base+index+1, index, params))
    signal.signal(signal.SIGTERM, lambda *_: STOP.set())
    signal.signal(signal.SIGINT, lambda *_: STOP.set())
    with ThreadPoolExecutor(max_workers=int(os.getenv('MAX_PARALLEL','4'))) as pool:
        results = list(pool.map(run_one, jobs))
    subprocess.run([sys.executable, str(ROOT/'experiments/summarize_matrix.py'), str(result_root)], check=True)
    return 0 if all(results) else 1


if __name__ == '__main__':
    sys.exit(main())
