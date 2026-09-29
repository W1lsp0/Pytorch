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
    retry_dependency=Path(plan.get('retry_wait_for_queue_done', '')) if plan.get('retry_wait_for_queue_done') else None
    remote_dependency=plan.get('remote_wait_for_queue_done')
    def remote_done():
        if not remote_dependency:return True
        try:
            r=subprocess.run(['ssh','-i','/data1/lab409/W1lsp0/ssh_config/id_rsa_spug','-p','2222','-o','BatchMode=yes','-o','ConnectTimeout=10','user@59.67.152.228','test -f '+remote_dependency],timeout=20)
            return r.returncode==0
        except Exception:return False
    while not dependency.exists() or (retry_dependency and not retry_dependency.exists()) or not remote_done():
        save(ROOT/'health.json',dict(checked_at=time.time(),status='waiting_for_v13_queues',dependency=str(dependency),remote_dependency=remote_dependency,warnings=[]))
        time.sleep(30)
    control=Path(plan['result_root'])/'control'
    # Node lock plus existing launch record prevent a second queue on restart.
    record=ROOT/'launch.json'
    if not record.exists():
        with (ROOT/'supervisor.log').open('a') as log:
            child=subprocess.Popen([sys.executable,str(Path(plan['source'])/'experiments/supervise_dynamic.py'),str(ROOT/'local_plan.json')],cwd=plan['source'],stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
        save(record,dict(pid=child.pid,started_at=time.time(),dependency_success=json.loads(dependency.read_text()).get('success')))
        if plan.get('remote_plan'):
            cmd="/home/user/anaconda3/envs/zjk/bin/python /mnt/data/zjk/TTFL/v14_probation_weight_monitor/source/experiments/supervise_dynamic.py /mnt/data/zjk/TTFL/v14_probation_weight_monitor/remote_plan.json"
            subprocess.run(['ssh','-i','/data1/lab409/W1lsp0/ssh_config/id_rsa_spug','-p','2222','-o','BatchMode=yes','user@59.67.152.228','mkdir -p /mnt/data/zjk/TTFL/v14_probation_weight_monitor'],check=True,timeout=20)
            subprocess.run(['ssh','-i','/data1/lab409/W1lsp0/ssh_config/id_rsa_spug','-p','2222','-o','BatchMode=yes','user@59.67.152.228','nohup '+cmd+' >> /mnt/data/zjk/TTFL/v14_probation_weight_monitor/remote_supervisor.log 2>&1 < /dev/null &'],check=True,timeout=20)
    while True:
        health=dict(checked_at=time.time(),warnings=[])
        if plan.get('remote_plan'):
            try:
                subprocess.run(['rsync','-az','--exclude=control/','-e','ssh -i /data1/lab409/W1lsp0/ssh_config/id_rsa_spug -p 2222 -o BatchMode=yes -o ConnectTimeout=10','user@59.67.152.228:'+plan['remote_plan']['result_root']+'/',str(ROOT/'remote_archive')+'/'],check=True,timeout=90,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            except Exception as exc:health['warnings'].append('remote sync: '+str(exc))
        try:
            node=json.loads((control/'monitor_status.json').read_text())
            health['local']=node
            if not all(r['status'] in ('success','failure') for r in node['runs']) and time.time()-node['checked_at']>120:
                health['warnings'].append('stale supervisor heartbeat')
            health['warnings'].extend(node.get('warnings',[]))
        except Exception as exc:health['warnings'].append(str(exc))
        if plan.get('remote_plan'):
            try:
                remote_control = plan['remote_plan']['result_root'] + '/control/monitor_status.json'
                rr=subprocess.run(['ssh','-i','/data1/lab409/W1lsp0/ssh_config/id_rsa_spug','-p','2222','-o','BatchMode=yes','user@59.67.152.228','cat '+remote_control],capture_output=True,text=True,timeout=25,check=True)
                health['remote']=json.loads(rr.stdout)
            except Exception as exc:health['warnings'].append('remote: '+str(exc))
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
