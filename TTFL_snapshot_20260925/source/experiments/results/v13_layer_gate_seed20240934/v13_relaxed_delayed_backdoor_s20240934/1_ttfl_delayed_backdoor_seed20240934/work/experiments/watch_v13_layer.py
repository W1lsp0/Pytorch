#!/usr/bin/env python3
"""Monitor V13 local/remote supervisors and produce a strict pair report."""
import json, subprocess, time
from pathlib import Path

ROOT=Path(__file__).resolve().parent/'results/v13_layer_gate_monitor'; SSH=['ssh','-i','/data1/lab409/W1lsp0/ssh_config/id_rsa_spug','-p','2222','-o','BatchMode=yes','-o','ConnectTimeout=10','user@59.67.152.228']
def write_reminder(report_path):
    marker=Path('/data1/lab409/W1lsp0/EXPERIMENT_COMPLETE_REMINDER.json')
    marker.write_text(json.dumps({'batch':'v13_layer_gate','completed_at':time.time(),'report':str(report_path),'validation_complete':True,'goal_achieved':False,'action':'Read the V13 paired report and continue optimization; batch completion is not research success.'},indent=2)+'\n')
def sync_remote():
    dest=ROOT/'remote_archive'; dest.mkdir(parents=True,exist_ok=True)
    try:
        subprocess.run(['rsync','-az','--exclude=control','-e','ssh -i /data1/lab409/W1lsp0/ssh_config/id_rsa_spug -p 2222 -o BatchMode=yes -o ConnectTimeout=10','user@59.67.152.228:/mnt/data/zjk/TTFL/results/v13_layer_gate_seed20240935/',''+str(dest)+'/'],timeout=90,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    except Exception: pass
def read_remote():
    try:
        p=subprocess.run(SSH+['cat /mnt/data/zjk/TTFL/v13_layer_gate_seed20240935/control/monitor_status.json'],capture_output=True,text=True,timeout=25,check=True); return json.loads(p.stdout)
    except Exception as e: return {'host':'remote','error':str(e),'runs':[]}
def main():
    while True:
        sync_remote()
        local={}
        try: local=json.loads((ROOT/'local_plan.json').read_text())
        except Exception: pass
        statuses=[]
        for plan in (ROOT/'local_plan.json',):
            try:
                p=json.loads(plan.read_text()); c=Path(p['result_root'])/'control/monitor_status.json'; d=json.loads(c.read_text()); statuses += d.get('runs',[])
            except Exception: pass
        remote=read_remote(); statuses += remote.get('runs',[])
        (ROOT/'health.json').write_text(json.dumps({'checked_at':time.time(),'local_runs':statuses[:6],'remote':remote},indent=2)+'\n')
        if all(s.get('status') in ('success','failure') for s in statuses) and len(statuses)>=12:
            try:
                subprocess.run(['python',str(Path(__file__).with_name('report_v13_layer_gate.py')),str(ROOT/'pairs.json')],check=True)
                write_reminder(ROOT/'matched_report.json')
            except Exception as e: (ROOT/'report_error.txt').write_text(str(e))
            return
        time.sleep(30)
if __name__=='__main__': main()
