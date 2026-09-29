#!/usr/bin/env python3
"""Host-local work queue with memory admission and restart-safe launch records."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from supervise_v11_node import inspect, processes_under, save


def choose_gpu(resources, reserved, required_mib):
    # Full 20-client trials peak near 19 GiB. Do not colocate with foreign
    # processes: their future memory demand is unknown on shared machines.
    candidates = [g for g, r in resources.items() if g not in reserved
                  and not r['compute_pids'] and r['used_mib'] <= 500
                  and r['utilization'] <= 10 and r['free_mib'] >= required_mib]
    return max(candidates, key=lambda g: (resources[g]['free_mib'], -int(g)), default=None)


def resources():
    out = subprocess.check_output(['nvidia-smi', '--query-gpu=index,uuid,memory.total,memory.used,utilization.gpu', '--format=csv,noheader,nounits'], text=True, timeout=20)
    gpu = {}
    uuids = {}
    for line in out.splitlines():
        i, uuid, total, used, util = [s.strip() for s in line.split(',')]
        gpu[i] = dict(total_mib=int(total), used_mib=int(used), free_mib=int(total)-int(used), utilization=int(util), compute_pids=[])
        uuids[uuid] = i
    out = subprocess.check_output(['nvidia-smi', '--query-compute-apps=gpu_uuid,pid', '--format=csv,noheader,nounits'], text=True, timeout=20)
    for line in out.splitlines():
        uuid, pid = [s.strip() for s in line.split(',')]
        if uuid in uuids:
            gpu[uuids[uuid]]['compute_pids'].append(int(pid))
    return gpu


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('plan', type=Path); args = ap.parse_args()
    plan = json.loads(args.plan.read_text()); root = Path(plan['result_root'])
    control = root/'control'; control.mkdir(parents=True, exist_ok=True)
    (root/'logs').mkdir(exist_ok=True)
    lock = (control/'supervisor.lock').open('a'); fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    (control/'supervisor.pid').write_text(str(os.getpid()))
    children = {}
    while True:
        warnings = []; states = []; reserved = set()
        try:
            gpu = resources()
        except Exception as exc:
            save(control/'monitor_error.json', dict(time=time.time(), error=str(exc)))
            time.sleep(30); continue
        for job in plan['jobs']:
            matrix = root/job['name']; state = inspect(matrix)
            rec = control/(job['name']+'.launch.json')
            launch = json.loads(rec.read_text()) if rec.exists() else {}
            state.update(name=job['name'], gpu=launch.get('gpu'), pid=launch.get('pid'))
            child = children.get(job['name'])
            live = processes_under(matrix) if launch else []
            launcher_live = child is not None and child.poll() is None
            if launch and state['status'] not in ('success','failure'):
                if live or launcher_live:
                    if state['status']=='absent': state['status']='starting'
                else:
                    state['status']='launcher_lost'
                    state['warnings'].append('launch recorded but no live processes or completion; manual recovery required')
            elif not launch and state['status']=='absent': state['status']='queued'
            if launch and (live or launcher_live or state['status'] in ('running','starting')):
                reserved.add(launch['gpu'])
            states.append(state)
        for job, state in zip(plan['jobs'], states):
            if state['status']!='queued': continue
            chosen = choose_gpu(gpu, reserved, job.get('required_free_mib',21000))
            if chosen is None: continue
            matrix = root/job['name']
            env = dict(os.environ, **plan['environment'], **job['environment'], GPU_VISIBLE_LIST=chosen, RESULT_ROOT=str(matrix))
            with (root/'logs'/(job['name']+'.queue.log')).open('a') as log:
                child = subprocess.Popen([sys.executable, str(Path(plan['source'])/'experiments/run_parallel_matrix.py')], cwd=plan['source'], env=env, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
            children[job['name']] = child; reserved.add(chosen)
            save(control/(job['name']+'.launch.json'), dict(pid=child.pid, gpu=chosen, time=time.time(), environment=dict(plan['environment'], **job['environment'], GPU_VISIBLE_LIST=chosen, RESULT_ROOT=str(matrix))))
            state.update(status='starting', gpu=chosen, pid=child.pid)
        for state in states:
            warnings.extend(state['name']+': '+w for w in state['warnings'])
            if state['status']=='failure': warnings.append(state['name']+': training failed')
        save(control/'monitor_status.json', dict(checked_at=time.time(), host=plan['host'], gpus=gpu, runs=states, warnings=warnings))
        if all(s['status'] in ('success','failure') for s in states) and not reserved:
            save(control/'queue_done.json', dict(time=time.time(), success=all(s['status']=='success' for s in states))); return
        time.sleep(30)

if __name__=='__main__': main()
