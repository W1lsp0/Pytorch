#!/usr/bin/env python3
"""Pair a new-seed risk-gate baseline and attenuation ablation."""
import argparse
import json
from pathlib import Path
from compare_probe_conditions import artifacts, FIELDS
from report_trigger_delta import validate_frozen_source, validate_scores
import re
import csv
from report_long_window import read_run

SCENARIOS=('none','backdoor','delayed_backdoor')

def index(matrix):
    out={}
    for p in matrix.glob('*/manifest.json'):
        m=json.loads(p.read_text())
        key=(m['scenario'],m['seed'])
        assert key not in out, ('duplicate condition',key)
        out[key]=(p.parent,m)
    return out

def validate_pair_manifest(candidate, baseline, seed):
    for manifest,power in ((candidate,0.0),(baseline,1.0)):
        assert manifest['method']=='ttfl' and manifest['seed']==seed
        assert manifest['rounds']==30 and manifest['clients']==20
        assert manifest.get('trigger_score_mode')=='clean_delta'
        assert float(manifest['risk_raw_attenuation_power'])==power
    assert all(candidate[k]==baseline[k] for k in (*FIELDS,'known_trigger_probe','heavy_probe_rotate_mod','trigger_score_mode')), 'paired protocol mismatch'


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('candidate',type=Path); ap.add_argument('--baseline',type=Path,required=True); ap.add_argument('--seed',type=int,required=True); a=ap.parse_args()
    cand,base=index(a.candidate),index(a.baseline); expected={(s,a.seed) for s in SCENARIOS}
    assert set(cand)==expected and set(base)==expected, (set(cand),set(base),expected)
    pairs=[]
    for key in sorted(expected):
        cr,cm=cand[key]; br,bm=base[key]
        validate_pair_manifest(cm,bm,a.seed)
        assert cm['scenario']==bm['scenario']==key[0]
        for run,m,matrix in ((cr,cm,a.candidate),(br,bm,a.baseline)):
            protocol=json.loads((matrix/'frozen_protocol.json').read_text())
            validate_frozen_source(run,protocol)
            assert m['known_trigger_probe'] and m['heavy_probe_rotate_mod']==1 and m['local_epochs']==1
            assert m['poison_rate']==1.0 and m['attack_stop_round']==0
            assert m['attack_start_round']==(11 if key[0]=='delayed_backdoor' else 1)
            assert m['malicious_client_ids']==([] if key[0]=='none' else [1])
            raw=[json.loads(x) for x in (run/'round_metrics.jsonl').read_text().splitlines() if x.strip()]
            assert [r['round'] for r in raw]==list(range(1,31))
            for row in raw:
                validate_scores(row)
            if m['malicious_client_ids']:
                text=(run/'client_1.log').read_text()
                actual=[(int(n),flag=='True') for n,flag in re.findall(r'Round (\d+) [^\n]*attack_active=(True|False)',text)]
                assert actual==[(n,n>=m['attack_start_round']) for n in range(1,31)], 'attack schedule mismatch'
        ca,ba=artifacts(cr,cm),artifacts(br,bm)
        assert ca['initial_sha256']==ba['initial_sha256'] and ca['partition_sha256']==ba['partition_sha256']
        assert ca['training_sha256']==ba['training_sha256'], 'training code mismatch'
        # Snapshot-wide hashes also include analysis scripts, which can evolve during a run.
        # Training-source content hashes above are the controlled comparison.
        baseline=read_run(br); candidate=read_run(cr)
        pairs.append(dict(scenario=key[0],seed=a.seed,baseline=baseline,candidate=candidate,
                          delta_percentage_points={k:100*(candidate[k]-baseline[k]) if candidate[k] is not None and baseline[k] is not None else None for k in ('final_accuracy','final_asr','attack_window_mean_asr','attack_window_peak_asr','normal_mean_exclusion','normal_ever_excluded_rate')},
                          fairness={'baseline':ba,'candidate':ca}))
    assert len({p['fairness']['candidate']['training_sha256'] for p in pairs})==1, 'training changed across scenarios'
    groups=[]
    for p in pairs:
        groups.append(dict(scenario=p['scenario'],n=1,baseline={k:p['baseline'][k] for k in ('final_accuracy','final_asr','attack_window_mean_asr','attack_window_peak_asr','normal_mean_exclusion')},candidate={k:p['candidate'][k] for k in ('final_accuracy','final_asr','attack_window_mean_asr','attack_window_peak_asr','normal_mean_exclusion')},delta_percentage_points=p['delta_percentage_points']))
    payload={'complete':True,'seed':a.seed,'definition':'clean_delta retained; risk attenuation power baseline 1.0 vs candidate 0.0; this affects BOTH layer admission and normalized aggregation weights; isolation and blacklist rules unchanged','pairs':pairs,'groups':groups,'limitations':'One independent seed and known trigger probe; descriptive paired evidence only.'}
    (a.candidate/'risk_gate_independent_report.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n')
    lines=['# 风险 EMA 聚合门控独立种子配对验证','',f'独立种子 `{a.seed}`；基线幂为 1.0，候选幂为 0.0。两者固定 clean_delta、隔离/黑名单规则、初始化和分片。风险衰减同时用于层准入和归一化权重，本实验不能将这两处影响分开。', '', '| 场景 | 基线/候选准确率 | 基线/候选最终 ASR | 基线/候选攻击窗口 ASR | 基线/候选正常排除率 | 排除率变化（百分点） |','|---|---:|---:|---:|---:|---:|']
    for g in groups:
        f=lambda k:f"{100*g['baseline'][k]:.2f}% / {100*g['candidate'][k]:.2f}%"
        lines.append(f"| {g['scenario']} | {f('final_accuracy')} | {f('final_asr')} | {f('attack_window_mean_asr') if g['baseline']['attack_window_mean_asr'] is not None else 'n/a'} | {f('normal_mean_exclusion')} | {g['delta_percentage_points']['normal_mean_exclusion']:+.2f} |")
    lines += ['', '该报告仅提供一个独立种子的配对描述，不能作显著性或最终泛化结论。']
    lines += ['', '| 场景 | 基线/候选攻击窗口峰值 ASR | 基线/候选 C1 首次攻击后完全排除 |', '|---|---:|---|']
    for pair in pairs:
        values=[]
        for v in ('baseline','candidate'):
            event=(pair[v]['attacker_exclusion'] or {}).get('1')
            values.append('n/a' if event is None else str(event['first_excluded_round_after_start'])+' ('+event['status']+')')
        peak=pair['baseline']['attack_window_peak_asr']
        peak_text='n/a' if peak is None else f"{100*peak:.2f}% / {100*pair['candidate']['attack_window_peak_asr']:.2f}%"
        lines.append('| '+pair['scenario']+' | '+peak_text+' | '+' / '.join(values)+' |')
    with (a.candidate/'risk_gate_independent_curves.csv').open('w',newline='') as f:
        w=csv.writer(f); w.writerow(['scenario','variant','round','accuracy','asr','honest_exclusion'])
        for pair in pairs:
            for variant in ('baseline','candidate'):
                r=pair[variant]
                for i in range(30):
                    w.writerow([pair['scenario'],variant,i+1,r['clean_accuracy'][i],r['backdoor_asr'][i],r['normal_exclusion_by_round'][i]])
    (a.candidate/'risk_gate_independent_report.md').write_text('\n'.join(lines)+'\n')
    print(a.candidate/'risk_gate_independent_report.md')
if __name__=='__main__': main()
