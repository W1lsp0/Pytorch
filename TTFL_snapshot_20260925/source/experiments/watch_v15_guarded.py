#!/usr/bin/env python3
import fcntl,json,os,subprocess,sys,time
from pathlib import Path
from supervise_v11_node import save
from report_v15_guarded import write_reports,screen
ROOT=Path(__file__).resolve().parent/'results/v15_guarded_floor_monitor'
def main():
 lock=(ROOT/'watcher.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);(ROOT/'watcher.pid').write_text(str(os.getpid()))
 plan=json.loads((ROOT/'local_plan.json').read_text()); dep=Path(plan['wait_for_queue_done']); rdep=plan['remote_plan']['wait_for_queue_done']
 while not dep.exists(): save(ROOT/'health.json',{'checked_at':time.time(),'status':'waiting_for_v14','warnings':[]});time.sleep(30)
 rec=ROOT/'launch.json'
 if not rec.exists():
  with (ROOT/'supervisor.log').open('a') as log: child=subprocess.Popen([sys.executable,str(Path(plan['source'])/'experiments/supervise_dynamic.py'),str(ROOT/'local_plan.json')],cwd=plan['source'],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  save(rec,{'pid':child.pid,'started_at':time.time()})
  cmd='/home/user/anaconda3/envs/zjk/bin/python /mnt/data/zjk/TTFL/v15_guarded_floor_monitor/source/experiments/supervise_dynamic.py /mnt/data/zjk/TTFL/v15_guarded_floor_monitor/remote_plan.json'
  subprocess.run(['ssh','-i','/data1/lab409/W1lsp0/ssh_config/id_rsa_spug','-p','2222','-o','BatchMode=yes','user@59.67.152.228','nohup '+cmd+' >> /mnt/data/zjk/TTFL/v15_guarded_floor_monitor/remote_supervisor.log 2>&1 < /dev/null &'],check=True,timeout=30)
 archive=ROOT/'remote_archive';archive.mkdir(exist_ok=True)
 last_sync=0
 while True:
  h={'checked_at':time.time(),'warnings':[]}
  try:h['local']=json.loads(((Path(plan['result_root'])/'control')/'monitor_status.json').read_text())
  except Exception as e:h['warnings'].append('local: '+str(e))
  try:
   rr=subprocess.run(['ssh','-i','/data1/lab409/W1lsp0/ssh_config/id_rsa_spug','-p','2222','-o','BatchMode=yes','user@59.67.152.228','cat '+plan['remote_plan']['result_root']+'/control/monitor_status.json'],capture_output=True,text=True,timeout=30,check=True);h['remote']=json.loads(rr.stdout)
  except Exception as e:h['warnings'].append('remote: '+str(e))
  for host in ('local','remote'):
   h['warnings'].extend(host+': '+w for w in h.get(host,{}).get('warnings',[]))
  remote_runs=h.get('remote',{}).get('runs',[])
  all_remote_terminal=bool(remote_runs) and all(r['status'] in ('success','failure') for r in remote_runs)
  if time.time()-last_sync>=300 or (all_remote_terminal and not (archive/'control_sync_complete.json').exists()):
   try:
    subprocess.run(['rsync','-az','--exclude=control/','-e','ssh -i /data1/lab409/W1lsp0/ssh_config/id_rsa_spug -p 2222 -o BatchMode=yes -o ConnectTimeout=10','user@59.67.152.228:'+plan['remote_plan']['result_root']+'/',str(archive)+'/'],capture_output=True,text=True,check=True,timeout=90)
    last_sync=time.time()
    if all_remote_terminal:save(archive/'control_sync_complete.json',{'synced_at':last_sync})
   except Exception as e:h['warnings'].append('remote sync: '+str(e))
  h['remote_last_sync']=last_sync
  try:
   report=write_reports(ROOT/'pairs.json');h['report_complete']=report['complete']; dec=screen(report);save(ROOT/'decision.json',dec)
  except Exception as e:h['warnings'].append(str(e));report={'complete':False}
  save(ROOT/'health.json',h)
  if report['complete']:
   event={'batch':'v15_guarded_floor','completed_at':time.time(),'validation_complete':True,'goal_achieved':dec['goal_achieved'],'report':str(ROOT/'matched_report.json'),'decision':dec};save(ROOT/'closeout.json',event);save(Path('/data1/lab409/W1lsp0/EXPERIMENT_COMPLETE_REMINDER.json'),event);return
  time.sleep(30)
if __name__=='__main__':main()
