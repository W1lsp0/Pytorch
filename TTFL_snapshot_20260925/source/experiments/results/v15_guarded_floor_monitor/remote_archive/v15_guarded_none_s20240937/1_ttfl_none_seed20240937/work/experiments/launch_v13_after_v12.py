#!/usr/bin/env python3
"""Start the next paired experiment only after the current V12 queue closes."""
import json, os, subprocess, time
from pathlib import Path

HERE=Path(__file__).resolve().parent
MON=HERE/'results/v12_matched_monitor'
OUT=HERE/'results/v13_layer_gate_monitor'
PY='/data1/anaconda3/envs/W1lsp0/bin/python'
SSH=['ssh','-i','/data1/lab409/W1lsp0/ssh_config/id_rsa_spug','-p','2222','-o','BatchMode=yes','-o','ConnectTimeout=10','user@59.67.152.228']

def terminal():
    try:
        d=json.loads((MON/'health.json').read_text())
        return all(r.get('status') in ('success','failure') for h in ('local','remote') for r in d[h]['runs']) and not any(r['name']=='absent' for r in [])
    except Exception:
        return False

def main():
    OUT.mkdir(parents=True,exist_ok=True); marker=OUT/'launch.json'
    while not marker.exists():
        if terminal(): break
        time.sleep(30)
    if marker.exists(): return
    lp=OUT/'local_plan.json'; rp=OUT/'remote_plan.json'
    lp_log=(OUT/'local_supervisor.log').open('a')
    local=subprocess.Popen([PY,str(HERE/'supervise_v11_node.py'),str(lp)],stdin=subprocess.DEVNULL,stdout=lp_log,stderr=subprocess.STDOUT,start_new_session=True)
    lp_log.close()
    remote_plan='/mnt/data/zjk/TTFL/v13_layer_gate_monitor/remote_plan.json'
    cmd=f"mkdir -p /mnt/data/zjk/TTFL/v13_layer_gate_monitor; nohup /home/user/anaconda3/envs/zjk/bin/python /mnt/data/zjk/TTFL/v13_source/experiments/supervise_v11_node.py {remote_plan} >> /mnt/data/zjk/TTFL/v13_layer_gate_monitor/remote_supervisor.log 2>&1 < /dev/null & echo $!"
    rr=subprocess.run(SSH+[cmd],text=True,capture_output=True,timeout=30,check=True)
    marker.write_text(json.dumps({'started_at':time.time(),'local_pid':local.pid,'remote_pid':rr.stdout.strip(),'reason':'v12 terminal'},indent=2)+'\n')
if __name__=='__main__': main()
