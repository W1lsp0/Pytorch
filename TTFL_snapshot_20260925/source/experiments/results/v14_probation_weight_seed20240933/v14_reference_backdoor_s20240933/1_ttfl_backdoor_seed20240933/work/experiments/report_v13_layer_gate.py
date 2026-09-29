#!/usr/bin/env python3
"""Audit paired V13 runs changing only the layer gate scale."""
import argparse, json, time
from pathlib import Path
from compare_probe_conditions import FIELDS, artifacts
from report_long_window import read_run
from report_v12_matched import validate_schedule
from supervise_v11_node import save

def status(p):
    q=p/'completion.json'
    return json.loads(q.read_text()).get('status') if q.exists() else 'pending'

def one(base, relaxed):
    result={'baseline':str(base),'candidate':str(relaxed),'statuses':[status(base),status(relaxed)],'validation':'pending'}
    if result['statuses'] != ['success','success']:
        if 'failure' in result['statuses']: result['validation']='failed_run'
        return result
    bm,cm=[json.loads((p/'manifest.json').read_text()) for p in (base,relaxed)]
    fixed=(*FIELDS,'known_trigger_probe','heavy_probe_rotate_mod','trigger_score_mode','risk_raw_attenuation_power','risk_cross_channel_guard','risk_soft_probation','risk_soft_probation_reference_exclude','risk_soft_probation_c2_exclude','risk_low_entropy_probe_guard','risk_soft_probation_c2_streak','risk_low_entropy_probe_h','risk_low_entropy_probe_acc','risk_low_entropy_probe_streak')
    mismatch=[k for k in fixed if k not in bm or k not in cm or bm[k]!=cm[k]]
    if mismatch: raise ValueError(f'paired mismatch: {mismatch}')
    if (float(bm.get('layer_gate_lambda',-1)),float(cm.get('layer_gate_lambda',-1))) != (0.15,0.05):
        raise ValueError('expected layer gate lambda 0.15 -> 0.05')
    ba,ca=artifacts(base,bm),artifacts(relaxed,cm)
    if ba['initial_sha256']!=ca['initial_sha256'] or ba['partition_sha256']!=ca['partition_sha256']:
        raise ValueError('initialization/partition differs')
    if ba['training_sha256']!=ca['training_sha256']:
        raise ValueError('training source differs')
    validate_schedule(base,bm); validate_schedule(relaxed,cm)
    br,cr=read_run(base),read_run(relaxed)
    keys=('final_accuracy','final_asr','attack_window_mean_asr','attack_window_peak_asr','normal_mean_exclusion','normal_ever_excluded_rate')
    result.update(validation='validated',scenario=bm['scenario'],seed=bm['seed'],metrics_baseline={k:br[k] for k in keys},metrics_candidate={k:cr[k] for k in keys},delta={k:None if br[k] is None else cr[k]-br[k] for k in keys},evidence={'baseline':ba,'candidate':ca})
    return result

def write_reports(spec_path):
    spec=json.loads(spec_path.read_text())
    rows=[]
    for p in spec['pairs']:
        try: rows.append({**p, **one(Path(p['baseline']),Path(p['candidate']))})
        except Exception as e: rows.append(dict(p,validation='audit_failed',error=str(e)))
    complete=all(r['validation']=='validated' for r in rows)
    out=spec_path.parent; report={'checked_at':time.time(),'complete':complete,'goal_achieved':False,'pairs':rows,'scope':'V13 changes only the layer gate lambda from 0.15 to 0.05, with all V12 probation/low-entropy switches held on. Same-host seed pairs are required; this is a layer-gate ablation, not a final security claim.'}
    save(out/'matched_report.json',report)
    lines=['# V13 layer gate paired audit','',report['scope'],'','| pair | validation | accuracy | final ASR | attack mean ASR | normal exclusion |','|---|---|---:|---:|---:|---:|']
    f=lambda x:'n/a' if x is None else f'{100*x:.2f}%'
    for r in rows:
        if 'metrics_baseline' not in r: lines.append(f"| {r['name']} | {r['validation']} | — | — | — | — |") ; continue
        b,c=r['metrics_baseline'],r['metrics_candidate']; lines.append('| '+' | '.join([r['name'],r['validation']]+[f(b[k])+' → '+f(c[k]) for k in ('final_accuracy','final_asr','attack_window_mean_asr','normal_mean_exclusion')])+' |')
    (out/'matched_report.md').write_text('\n'.join(lines)+'\n')
    return report

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('spec',type=Path); args=ap.parse_args()
    report=write_reports(args.spec)
    print(json.dumps({'complete':report['complete'],'validations':{r['name']:r['validation'] for r in report['pairs']}}))
if __name__=='__main__': main()
