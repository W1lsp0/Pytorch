#!/usr/bin/env python3
"""Compare clean-delta TTFL with and without risk attenuation in layer gating."""
import argparse
import json
import statistics
from pathlib import Path
from report_long_window import read_run

SCENARIOS=('none','backdoor','delayed_backdoor')
SEEDS=(20240925,20240926)

def index(matrix):
    out={}
    for p in matrix.glob('*/manifest.json'):
        m=json.loads(p.read_text()); out[(m['scenario'],m['seed'])]=(p.parent,m)
    return out

def mean_sd(xs):
    return {'mean':statistics.mean(xs),'sd':statistics.stdev(xs)}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('matrix',type=Path); ap.add_argument('--reference',type=Path,required=True); a=ap.parse_args()
    new,old=index(a.matrix),index(a.reference); expected={(s,seed) for s in SCENARIOS for seed in SEEDS}
    assert set(new)==expected and set(old)==expected
    pairs=[]
    for key in sorted(expected):
        nr,nm=new[key]; br,bm=old[key]
        for m in (nm,bm):
            assert m['method']=='ttfl' and m['scenario']==key[0] and m['seed']==key[1]
            assert m.get('trigger_score_mode', 'legacy')=='clean_delta'
            assert m['rounds']==30 and m['clients']==20
        assert float(nm['risk_raw_attenuation_power'])==0
        assert float(bm.get('risk_raw_attenuation_power', 1.0))==1.0
        assert nm['initial_model_sha256']==bm['initial_model_sha256'] if 'initial_model_sha256' in nm else True
        oldr,newr=read_run(br),read_run(nr)
        pairs.append(dict(scenario=key[0],seed=key[1],baseline=oldr,candidate=newr))
    groups=[]
    for scenario in SCENARIOS:
        rows=[p for p in pairs if p['scenario']==scenario]
        def v(k,variant): return [p[variant][k] for p in rows]
        groups.append(dict(scenario=scenario,n=2,baseline={k:mean_sd(v(k,'baseline')) for k in ('final_accuracy','final_asr','normal_mean_exclusion')},candidate={k:mean_sd(v(k,'candidate')) for k in ('final_accuracy','final_asr','normal_mean_exclusion')},delta={k:mean_sd([p['candidate'][k]-p['baseline'][k] for p in rows]) for k in ('final_accuracy','final_asr','normal_mean_exclusion')}))
    payload={'complete':True,'definition':'clean_delta retained; RISK_RAW_ATTENUATION_POWER 1.0 -> 0.0; isolation and blacklist rules unchanged','pairs':pairs,'groups':groups,'limitations':'Two development seeds; known trigger probe; no independent validation claim.'}
    (a.matrix/'risk_gate_ablation_report.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n')
    lines=['# 风险 EMA 聚合门控消融','','候选保持 clean_delta 和所有风险隔离/黑名单规则，仅将层准入评分中的风险衰减幂从 1.0 改为 0.0。', '', '| 场景 | 基线/消融准确率 | 基线/消融最终 ASR | 基线/消融正常轮平均排除率 | 排除率变化（百分点） |','|---|---:|---:|---:|---:|']
    for g in groups:
        f=lambda k:f"{100*g['baseline'][k]['mean']:.2f}% / {100*g['candidate'][k]['mean']:.2f}%"
        lines.append(f"| {g['scenario']} | {f('final_accuracy')} | {f('final_asr')} | {f('normal_mean_exclusion')} | {100*g['delta']['normal_mean_exclusion']['mean']:+.2f} ± {100*g['delta']['normal_mean_exclusion']['sd']:.2f} |")
    lines += ['', 'JSON 保留全部逐运行审计数据。该消融仅回答风险衰减是否造成层门槛误排除，不代表完整方法改进。']
    (a.matrix/'risk_gate_ablation_report.md').write_text('\n'.join(lines)+'\n')
    print(a.matrix/'risk_gate_ablation_report.md')
if __name__=='__main__': main()
