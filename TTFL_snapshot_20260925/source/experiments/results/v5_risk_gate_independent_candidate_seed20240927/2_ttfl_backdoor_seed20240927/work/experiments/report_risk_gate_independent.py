#!/usr/bin/env python3
"""Pair a new-seed risk-gate baseline and attenuation ablation."""
import argparse
import json
from pathlib import Path
from compare_probe_conditions import artifacts
from report_long_window import read_run

SCENARIOS=('none','backdoor','delayed_backdoor')

def index(matrix):
    out={}
    for p in matrix.glob('*/manifest.json'):
        m=json.loads(p.read_text()); out[(m['scenario'],m['seed'])]=(p.parent,m)
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('candidate',type=Path); ap.add_argument('--baseline',type=Path,required=True); ap.add_argument('--seed',type=int,required=True); a=ap.parse_args()
    cand,base=index(a.candidate),index(a.baseline); expected={(s,a.seed) for s in SCENARIOS}
    assert set(cand)==expected and set(base)==expected, (set(cand),set(base),expected)
    pairs=[]
    for key in sorted(expected):
        cr,cm=cand[key]; br,bm=base[key]
        for m,power in ((cm,0.0),(bm,1.0)):
            assert m['method']=='ttfl' and m['seed']==a.seed and m['rounds']==30 and m['clients']==20
            assert m.get('trigger_score_mode')=='clean_delta' and float(m.get('risk_raw_attenuation_power'))==power
        assert cm['scenario']==bm['scenario']==key[0]
        ca,ba=artifacts(cr,cm),artifacts(br,bm)
        assert ca['initial_sha256']==ba['initial_sha256'] and ca['partition_sha256']==ba['partition_sha256']
        assert cm['code_sha256']==bm['code_sha256']
        baseline=read_run(br); candidate=read_run(cr)
        pairs.append(dict(scenario=key[0],seed=a.seed,baseline=baseline,candidate=candidate,
                          delta_percentage_points={k:100*(candidate[k]-baseline[k]) if candidate[k] is not None and baseline[k] is not None else None for k in ('final_accuracy','final_asr','attack_window_mean_asr','normal_mean_exclusion','normal_ever_excluded_rate')},
                          fairness={'baseline':ba,'candidate':ca}))
    groups=[]
    for p in pairs:
        groups.append(dict(scenario=p['scenario'],n=1,baseline={k:p['baseline'][k] for k in ('final_accuracy','final_asr','attack_window_mean_asr','normal_mean_exclusion')},candidate={k:p['candidate'][k] for k in ('final_accuracy','final_asr','attack_window_mean_asr','normal_mean_exclusion')},delta_percentage_points=p['delta_percentage_points']))
    payload={'complete':True,'seed':a.seed,'definition':'clean_delta retained; risk attenuation power baseline 1.0 vs candidate 0.0; isolation and blacklist rules unchanged','pairs':pairs,'groups':groups,'limitations':'One independent seed and known trigger probe; descriptive paired evidence only.'}
    (a.candidate/'risk_gate_independent_report.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n')
    lines=['# 风险 EMA 聚合门控独立种子配对验证','',f'独立种子 `{a.seed}`；基线幂为 1.0，候选幂为 0.0。两者固定 clean_delta、隔离/黑名单规则、初始化和分片。', '', '| 场景 | 基线/候选准确率 | 基线/候选最终 ASR | 基线/候选攻击窗口 ASR | 基线/候选正常排除率 | 排除率变化（百分点） |','|---|---:|---:|---:|---:|---:|']
    for g in groups:
        f=lambda k:f"{100*g['baseline'][k]:.2f}% / {100*g['candidate'][k]:.2f}%"
        lines.append(f"| {g['scenario']} | {f('final_accuracy')} | {f('final_asr')} | {f('attack_window_mean_asr') if g['baseline']['attack_window_mean_asr'] is not None else 'n/a'} | {f('normal_mean_exclusion')} | {g['delta_percentage_points']['normal_mean_exclusion']:+.2f} |")
    lines += ['', '该报告仅提供一个独立种子的配对描述，不能作显著性或最终泛化结论。']
    (a.candidate/'risk_gate_independent_report.md').write_text('\n'.join(lines)+'\n')
    print(a.candidate/'risk_gate_independent_report.md')
if __name__=='__main__': main()
