#!/usr/bin/env python3
"""Start V14 after local V13 resources release, then audit all three arms."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from supervise_v11_node import save
from report_v14_weight import write_reports
from watch_v13_layer import screen

ROOT=Path(__file__).resolve().parent/'results/v14_probation_weight_monitor'

def main():
    lock=(ROOT/'watcher.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    (ROOT/'watcher.pid').write_text(str(os.getpid()))
    plan=json.loads((ROOT/'local_plan.json').read_text())
    dependency=Path(plan['wait_for_queue_done'])
    while not dependency.exists():
        save(ROOT/'health.json',dict(checked_at=time.time(),status='waiting_for_local_v13',dependency=str(dependency),warnings=[]))
        time.sleep(30)
    control=Path(plan['result_root'])/'control'
    # Node lock plus existing launch record prevent a second queue on restart.
    record=ROOT/'launch.json'
    if not record.exists():
        with (ROOT/'supervisor.log').open('a') as log:
            child=subprocess.Popen([sys.executable,str(Path(plan['source'])/'experiments/supervise_dynamic.py'),str(ROOT/'local_plan.json')],cwd=plan['source'],stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
        save(record,dict(pid=child.pid,started_at=time.time(),dependency_success=json.loads(dependency.read_text()).get('success')))
    while True:
        health=dict(checked_at=time.time(),warnings=[])
        try:
            node=json.loads((control/'monitor_status.json').read_text())
            health['local']=node
            if not all(r['status'] in ('success','failure') for r in node['runs']) and time.time()-node['checked_at']>120:
                health['warnings'].append('stale supervisor heartbeat')
            health['warnings'].extend(node.get('warnings',[]))
        except Exception as exc:health['warnings'].append(str(exc))
        try:
            report=write_reports(ROOT/'pairs.json')
            health['report_complete']=report['complete']
            health['warnings'].extend(p['name']+': '+p.get('error',p['validation']) for p in report['pairs'] if p['validation'] in ('audit_failed','failed_run'))
            decision=screen(report);save(ROOT/'decision.json',decision)
        except Exception as exc:
            health['warnings'].append(str(exc));report={'complete':False}
        save(ROOT/'health.json',health)
        if report['complete']:
            event=dict(batch='v14_probation_weight',completed_at=time.time(),validation_complete=True,goal_achieved=False,report=str(ROOT/'matched_report.json'),decision=decision)
            save(ROOT/'closeout.json',event)
            save(Path('/data1/lab409/W1lsp0/EXPERIMENT_COMPLETE_REMINDER.json'),event)
            return
        time.sleep(30)

if __name__=='__main__':main()
