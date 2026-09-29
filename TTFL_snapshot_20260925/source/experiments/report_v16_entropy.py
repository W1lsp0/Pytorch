#!/usr/bin/env python3
import argparse,json,time
from pathlib import Path
from compare_probe_conditions import FIELDS, artifacts
from report_long_window import read_run
from report_v12_matched import validate_schedule
from supervise_v11_node import save

def status(p):
 q=p/'completion.json'; return json.loads(q.read_text()).get('status') if q.exists() else 'pending'
def one(base,cand,comparison):
 out={'baseline':str(base),'candidate':str(cand),'statuses':[status(base),status(cand)],'validation':'pending'}
 if out['statuses']!=['success','success']:
  if 'failure' in out['statuses']: out['validation']='failed_run'
  return out
 bm,cm=[json.loads((p/'manifest.json').read_text()) for p in (base,cand)]
 fixed=(*FIELDS,'known_trigger_probe','heavy_probe_rotate_mod','trigger_score_mode','risk_raw_attenuation_power','risk_cross_channel_guard','layer_gate_lambda','risk_soft_probation_c2_streak','risk_low_entropy_probe_acc','risk_low_entropy_probe_streak')
 mismatch=[k for k in fixed if bm.get(k)!=cm.get(k)]
 if mismatch: raise ValueError(f'paired mismatch: {mismatch}')
 if bm.get('layer_gate_lambda')!=.15: raise ValueError('V16 keeps lambda=0.15')
 if cm.get('risk_probation_weight_floor')!=.25 or cm.get('risk_probation_floor_guard')!=True: raise ValueError('candidate must use guarded floor')
 if comparison=='original_guarded':
  if bm.get('risk_probation_weight_floor')!=0 or bm.get('risk_soft_probation')!=False: raise ValueError('bad original baseline')
 elif comparison=='guarded_entropy':
  if bm.get('risk_probation_weight_floor')!=.25 or bm.get('risk_probation_floor_guard')!=True: raise ValueError('bad floor baseline')
  switches=('risk_soft_probation','risk_soft_probation_reference_exclude','risk_soft_probation_c2_exclude','risk_low_entropy_probe_guard')
  if any(bm.get(k)!=cm.get(k) for k in switches): raise ValueError('guarded comparison must change only entropy threshold')
 else: raise ValueError('unknown comparison')
 if bm.get('risk_low_entropy_probe_h')!=.15 or cm.get('risk_low_entropy_probe_h')!=.01: raise ValueError('entropy threshold mismatch')
 ba,ca=artifacts(base,bm),artifacts(cand,cm)
 if any(ba[k]!=ca[k] for k in ('initial_sha256','partition_sha256','training_sha256')): raise ValueError('artifact mismatch')
 validate_schedule(base,bm); validate_schedule(cand,cm)
 br,cr=read_run(base),read_run(cand); keys=('final_accuracy','final_asr','attack_window_mean_asr','attack_window_peak_asr','normal_mean_exclusion','normal_ever_excluded_rate')
 out.update(validation='validated',scenario=bm['scenario'],seed=bm['seed'],metrics_baseline={k:br[k] for k in keys},metrics_candidate={k:cr[k] for k in keys},delta={k:None if br[k] is None else cr[k]-br[k] for k in keys},evidence={'baseline':ba,'candidate':ca}); return out

def write_reports(spec):
 d=json.loads(spec.read_text()); rows=[]
 for p in d['pairs']:
  try: rows.append({**p,**one(Path(p['baseline']),Path(p['candidate']),p['comparison'])})
  except Exception as e: rows.append({**p,'validation':'audit_failed','error':str(e)})
 report={'checked_at':time.time(),'complete':all(r['validation']=='validated' for r in rows),'goal_achieved':False,'pairs':rows,'scope':'V16 exploratory entropy threshold .01 versus V15 threshold .15; same-host and same-seed frozen-source comparisons.'}
 out=spec.parent; save(out/'matched_report.json',report)
 lines=['# V16 guarded probation floor paired audit','',report['scope'],'','| pair | validation | accuracy | final ASR | attack mean ASR | normal exclusion |','|---|---|---:|---:|---:|---:|']
 f=lambda x:'n/a' if x is None else f'{100*x:.2f}%'
 for r in rows:
  if 'metrics_baseline' not in r: lines.append(f"| {r['name']} | {r['validation']} | — | — | — | — |")
  else:
   b,c=r['metrics_baseline'],r['metrics_candidate'];lines.append('| '+' | '.join([r['name'],r['validation']]+[f(b[k])+' → '+f(c[k]) for k in ('final_accuracy','final_asr','attack_window_mean_asr','normal_mean_exclusion')])+' |')
 (out/'matched_report.md').write_text('\n'.join(lines)+'\n'); return report

def screen(report):
 regs=[]
 for p in report['pairs']:
  if p.get('validation')!='validated': continue
  for k in ('final_accuracy','final_asr','attack_window_mean_asr','attack_window_peak_asr','normal_mean_exclusion'):
   d=p.get('delta',{}).get(k)
   if d is None: continue
   bad=(k=='final_accuracy' and d<0) or (k in ('final_asr','attack_window_mean_asr','attack_window_peak_asr') and d>0) or (k=='normal_mean_exclusion' and d>=0)
   if bad: regs.append({'pair':p['name'],'metric':k,'delta':d})
 return {'status':'passed' if report['complete'] and not regs else 'not_met','regressions':regs,'goal_achieved':bool(report['complete'] and not regs),'next_action':'review V16 guarded floor' if regs else 'retain V16 guarded floor'}
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('spec',type=Path);a=ap.parse_args();r=write_reports(a.spec);save(a.spec.parent/'decision.json',screen(r));print(json.dumps({'complete':r['complete']}))
