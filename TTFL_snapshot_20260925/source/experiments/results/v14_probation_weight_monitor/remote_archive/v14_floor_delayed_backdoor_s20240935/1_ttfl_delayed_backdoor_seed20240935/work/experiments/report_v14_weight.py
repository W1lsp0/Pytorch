#!/usr/bin/env python3
"""Audit V14 weight-floor ablations and comparisons with the original baseline."""
import argparse, json, time
from pathlib import Path
from compare_probe_conditions import FIELDS, artifacts
from report_long_window import read_run
from report_v12_matched import validate_schedule
from supervise_v11_node import save

def status(p):
    q=p/'completion.json'
    return json.loads(q.read_text()).get('status') if q.exists() else 'pending'

def one(base, relaxed, comparison):
    result={'baseline':str(base),'candidate':str(relaxed),'statuses':[status(base),status(relaxed)],'validation':'pending'}
    if result['statuses'] != ['success','success']:
        if 'failure' in result['statuses']: result['validation']='failed_run'
        return result
    bm,cm=[json.loads((p/'manifest.json').read_text()) for p in (base,relaxed)]
    fixed=(*FIELDS,'known_trigger_probe','heavy_probe_rotate_mod','trigger_score_mode','risk_raw_attenuation_power','risk_cross_channel_guard','layer_gate_lambda','risk_soft_probation_c2_streak','risk_low_entropy_probe_h','risk_low_entropy_probe_acc','risk_low_entropy_probe_streak')
    mismatch=[k for k in fixed if k not in bm or k not in cm or bm[k]!=cm[k]]
    if mismatch: raise ValueError(f'paired mismatch: {mismatch}')
    if bm.get('layer_gate_lambda') != .15:
        raise ValueError('V14 keeps lambda=0.15')
    if (bm.get('risk_probation_weight_floor'), cm.get('risk_probation_weight_floor')) != (0.0,.25):
        raise ValueError('expected weight floor 0 -> 0.25')
    switches=('risk_soft_probation','risk_soft_probation_reference_exclude','risk_soft_probation_c2_exclude','risk_low_entropy_probe_guard')
    if comparison not in ('floor_ablation','original_reference'):
        raise ValueError('unknown comparison')
    expected_base = comparison == 'floor_ablation'
    if any(bm.get(k) != expected_base or cm.get(k) != True for k in switches):
        raise ValueError('unexpected risk switches')
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
        try: rows.append({**p, **one(Path(p['baseline']),Path(p['candidate']),p['comparison'])})
        except Exception as e: rows.append(dict(p,validation='audit_failed',error=str(e)))
    complete=all(r['validation']=='validated' for r in rows)
    out=spec_path.parent; report={'checked_at':time.time(),'complete':complete,'goal_achieved':False,'pairs':rows,'scope':'V14 floor ablation changes only probation weight floor 0 -> 0.25 at lambda=0.15. Original-reference comparisons also enable the four V12 switches and are composite comparisons. Seed 20240933 was used to develop the hypothesis; independent validation remains required.'}
    save(out/'matched_report.json',report)
    lines=['# V14 probation weight paired audit','',report['scope'],'','| pair | validation | accuracy | final ASR | attack mean ASR | normal exclusion |','|---|---|---:|---:|---:|---:|']
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
