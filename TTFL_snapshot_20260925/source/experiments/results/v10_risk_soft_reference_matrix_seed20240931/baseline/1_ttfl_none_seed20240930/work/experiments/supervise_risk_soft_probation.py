#!/usr/bin/env python3
"""Run a paired risk-soft-probation matrix with exclusive GPU leases."""
import concurrent.futures
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import time

from run_parallel_matrix import ROOT, run_one


def save(path, value):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    tmp.replace(path)


def main():
    study = ROOT / 'experiments/results/v9_risk_soft_probation_matrix_seed20240930'
    study.mkdir(exist_ok=True)
    lock = (study / 'supervisor.lock').open('w')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    (study / 'supervisor.pid').write_text(str(os.getpid()))
    if list(study.glob('*/*/manifest.json')):
        raise RuntimeError('refusing to overwrite existing study')
    gpus = queue.Queue()
    for gpu in ('0', '1', '2', '3', '4'):
        gpus.put(gpu)
    configs = []
    for variant, probation in (('baseline', 0), ('candidate', 1)):
        matrix = study / variant
        matrix.mkdir(exist_ok=True)
        for scenario in ('none', 'backdoor', 'delayed_backdoor'):
            params = dict(clients=20, rounds=30, epochs=1, attack_start=11,
                          attack_stop=0, poison_rate=1.0, known_probe=1,
                          probe_rotate=1, trigger_score_mode='clean_delta',
                          risk_raw_attenuation_power=1.0,
                          risk_cross_channel_guard=0,
                          risk_soft_probation=probation, timeout=10800)
            port = 24201 + len(configs)
            configs.append((matrix / f'{len(configs)+1}_ttfl_{scenario}_seed20240930',
                            scenario, port, params))
    sources = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in [*ROOT.glob('*.py'), *(ROOT/'server').rglob('*.py'),
                         *(ROOT/'Client').rglob('*.py')]}
    save(study / 'frozen_protocol.json', dict(
        created_at=datetime.datetime.now().astimezone().isoformat(), seed=20240930,
        source_files=sources, max_parallel=5, exclusive_gpu_per_run=True,
        python=sys.executable, candidate_default=False,
        intervention='risk soft streak remains audited and attenuated but does not exclude aggregation; blacklist/C2 quarantine remain hard',
        jobs=[dict(path=str(p), scenario=s, port=port, params=param) for p,s,port,param in configs]))

    def run(config):
        path, scenario, port, params = config
        gpu = gpus.get()
        try:
            return run_one((path, 'ttfl', scenario, 20240930, port, 0,
                            dict(params, gpus=gpu)))
        finally:
            gpus.put(gpu)

    def monitor():
        rows, warnings = [], []
        for path, scenario, port, _ in configs:
            status = (path/'status').read_text().strip() if (path/'status').exists() else 'queued'
            log = path/'work/log/server.log'
            content = log.read_text(errors='replace') if log.exists() else ''
            counts = re.findall(r'aggregate_(fit|evaluate): received (\d+) results and (\d+) failures', content)
            metrics = path/'work/log/round_metrics.jsonl'
            records = []
            if metrics.exists():
                for line in metrics.read_text().splitlines():
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
            current = records[-1] if records else {}
            if status == 'failure' or any(int(n) != 20 or int(f) for _, n, f in counts):
                warnings.append(str(path) + ': failure or unexpected returns')
            if status == 'running' and log.exists() and time.time() - log.stat().st_mtime > 900:
                warnings.append(str(path) + ': server log idle >900s')
            rows.append(dict(variant=path.parent.name, scenario=scenario, status=status,
                             fit=sum(x[0] == 'fit' for x in counts),
                             evaluate=sum(x[0] == 'evaluate' for x in counts),
                             audit_round=current.get('round', 0),
                             isolated_now=[cid for cid, a in current.get('risk_decision_audit', {}).items()
                                           if a.get('risk_isolated')],
                             gpu=json.loads((path/'manifest.json').read_text())['gpu_visible_list']
                             if (path/'manifest.json').exists() else None))
        state = dict(checked_at=datetime.datetime.now().astimezone().isoformat(),
                     verified_complete=False, warnings=warnings, runs=rows)
        save(study/'monitor_status.json', state)
        with (study/'monitor_events.jsonl').open('a') as f:
            f.write(json.dumps(state, ensure_ascii=False) + '\n')
        print(json.dumps(state, ensure_ascii=False), flush=True)
        return state

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(run, c) for c in configs]
        while True:
            monitor()
            if all(f.done() for f in futures):
                break
            concurrent.futures.wait(futures, timeout=30,
                                    return_when=concurrent.futures.ALL_COMPLETED)
        if not all(f.result() for f in futures):
            save(study/'closeout.json', dict(status='failed', reason='run failure'))
            return 1
    try:
        for variant in ('baseline', 'candidate'):
            matrix = study / variant
            for script in ('summarize_matrix.py', 'protocol_audit.py', 'diagnose_risk_isolation.py'):
                subprocess.run([sys.executable, str(ROOT/'experiments'/script), str(matrix)], check=True)
            audit = json.loads((matrix/'protocol_audit.json').read_text())
            if audit['run_count'] != 3 or audit['failed_runs']:
                raise RuntimeError('protocol audit failed')
        subprocess.run([sys.executable, str(ROOT/'experiments/report_risk_soft_probation.py'),
                        str(study/'baseline'), str(study/'candidate')], check=True)
        state = monitor()
        state['verified_complete'] = True
        save(study/'monitor_status.json', state)
        save(study/'closeout.json', dict(status='complete', verified_runs=6,
             report=str(study/'candidate/risk_soft_probation_report.md'),
             decision='Development result requires independent validation; probation remains off by default.'))
    except Exception as exc:
        save(study/'closeout.json', dict(status='audit_failed', error=str(exc)))
        raise
    return 0


if __name__ == '__main__':
    sys.exit(main())
