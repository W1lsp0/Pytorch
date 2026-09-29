#!/usr/bin/env python3
"""Persist both node states, sync evidence, and notify only on validated closeout."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import time
from report_v13_layer_gate import write_reports
from supervise_v11_node import save

ROOT=Path(__file__).resolve().parent/'results/v13_layer_gate_monitor'
SSH=['ssh','-i','/data1/lab409/W1lsp0/ssh_config/id_rsa_spug','-p','2222','-o','BatchMode=yes','-o','ConnectTimeout=10','user@59.67.152.228']


def screen(report):
    """Conservative descriptive screen; passing is not final research success."""
    if not report['complete']: return dict(status='pending', goal_achieved=False)
    failed=[]
    for row in report['pairs']:
        delta=row['delta']
        for key in ('final_asr','attack_window_mean_asr','attack_window_peak_asr'):
            if row['scenario']!='none' and delta[key] is not None and delta[key]>0:
                failed.append(dict(pair=row['name'],metric=key,delta=delta[key]))
        if delta['final_accuracy']<0: failed.append(dict(pair=row['name'],metric='final_accuracy',delta=delta['final_accuracy']))
        if delta['normal_mean_exclusion']>=0: failed.append(dict(pair=row['name'],metric='normal_mean_exclusion',delta=delta['normal_mean_exclusion']))
    return dict(status='not_met' if failed else 'development_screen_passed', regressions=failed,
                goal_achieved=False, next_action='Review mechanisms and choose next candidate' if failed else 'Validate against original baseline and new independent seeds',
                scope='Zero-tolerance descriptive screening of this ablation; not statistical significance or validation of the full research objective.')


def main():
    lock=(ROOT/'watcher.lock').open('a'); fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    (ROOT/'watcher.pid').write_text(str(os.getpid()))
    lp=json.loads((ROOT/'local_plan.json').read_text()); rp=json.loads((ROOT/'remote_plan.json').read_text())
    archive=ROOT/'remote_archive'; archive.mkdir(exist_ok=True)
    last_sync=0
    while True:
        health=dict(checked_at=time.time(),warnings=[]); all_terminal=True
        for host,plan in (('local',lp),('remote',rp)):
            try:
                path=Path(plan['result_root'])/'control/monitor_status.json'
                if host=='local': node=json.loads(path.read_text())
                else:
                    r=subprocess.run(SSH+['cat',str(path)],capture_output=True,text=True,timeout=25,check=True)
                    node=json.loads(r.stdout)
                expected={j['name'] for j in plan['jobs']}
                if {j['name'] for j in node['runs']}!=expected: raise ValueError('job roster differs from plan')
                terminal=all(s['status'] in ('success','failure') for s in node['runs'])
                if not terminal and time.time()-node['checked_at']>120: health['warnings'].append(host+': stale heartbeat')
                all_terminal &= terminal
                health[host]=node
                health['warnings'].extend(host+': '+w for w in node.get('warnings',[]))
            except Exception as exc:
                health['warnings'].append(host+': '+str(exc)); all_terminal=False
        if time.time()-last_sync>=300 or all_terminal:
            try:
                subprocess.run(['rsync','-az','--exclude=control/','-e','ssh -i /data1/lab409/W1lsp0/ssh_config/id_rsa_spug -p 2222 -o BatchMode=yes -o ConnectTimeout=10','user@59.67.152.228:'+rp['result_root']+'/',str(archive)+'/'],capture_output=True,text=True,check=True,timeout=60)
                last_sync=time.time()
            except Exception as exc: health['warnings'].append('archive sync: '+str(exc))
        try:
            report=write_reports(ROOT/'pairs.json')
            health['report_complete']=report['complete']
            health['warnings'].extend(r['name']+': '+r.get('error',r['validation']) for r in report['pairs'] if r['validation'] in ('audit_failed','failed_run'))
            decision=screen(report); save(ROOT/'decision.json',decision)
        except Exception as exc:
            health['warnings'].append('report: '+str(exc)); report={'complete':False}
        health['remote_last_sync']=last_sync
        save(ROOT/'health.json',health)
        with (ROOT/'health_events.jsonl').open('a') as f: f.write(json.dumps(health)+'\n')
        if report['complete']:
            reminder=dict(batch='v13_layer_gate',completed_at=time.time(),report=str(ROOT/'matched_report.json'),validation_complete=True,goal_achieved=False,decision=decision)
            save(ROOT/'closeout.json',reminder)
            save(Path('/data1/lab409/W1lsp0/EXPERIMENT_COMPLETE_REMINDER.json'),reminder)
            return
        time.sleep(30)

if __name__=='__main__':main()
