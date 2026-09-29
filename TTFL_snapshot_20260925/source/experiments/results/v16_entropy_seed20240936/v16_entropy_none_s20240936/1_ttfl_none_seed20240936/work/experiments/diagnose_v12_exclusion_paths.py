#!/usr/bin/env python3
"""Attribute observed exclusions to logged stages, without counterfactual claims."""
import json
import re
from pathlib import Path
from collections import Counter
from audit_records import load_audit


def diagnose(run):
    m=json.loads((run/'manifest.json').read_text()); rows,_=load_audit(run)
    stage={}; current=None
    for line in (run/'server.log').read_text(errors='replace').splitlines():
        start=re.search(r'第 (\d+) 轮 \| 审计阶段开始',line)
        if start: current=int(start[1])
        isolated=re.search(r'聚合隔离:.*Client IDs: ([0-9,]+)',line)
        if isolated and current is not None: stage[current]=set(isolated[1].split(','))
        if re.search(r'第 \d+ 轮聚合完成',line):current=None
    malicious=set(map(str,m['malicious_client_ids'])); counts=Counter()
    for row in rows:
        audits=row['risk_decision_audit']
        for cid,s in row['client_layer_stats'].items():
            group='attacker' if cid in malicious else 'normal'
            if s['included_layers']!=0:continue
            counts[group+':total_full']+=1
            if s.get('exclusion_reason')=='blacklist':counts[group+':pre_layer_blacklist']+=1
            elif cid in stage.get(row['round'],set()):counts[group+':aggregation_isolation']+=1
            else:
                counts[group+':layer_gate_without_logged_isolation']+=1
                a=audits.get(cid,{})
                if a.get('risk_prev',0)>=1-1e-12:
                    counts[group+':layer_gate_previous_risk_one']+=1
                elif a.get('risk_prev',0)>=.9:
                    counts[group+':layer_gate_previous_risk_at_least_0_9']+=1
            a=audits.get(cid,{})
            if a.get('low_entropy_probe_streak',0)>=2:counts[group+':low_guard_active_overlap']+=1
    return dict(run=str(run),scenario=m['scenario'],seed=m['seed'],counts=dict(counts),
        scope='Observed stage attribution only. Low-entropy overlaps may coincide with other gates. No saved raw_score or threshold per round in V12; cannot reconstruct score ranges or prove the effect of lowering lambda.')

if __name__=='__main__':
    root=Path(__file__).resolve().parent/'results/v12_low_entropy_guard_seed20240932'
    results=[]
    for manifest in sorted(root.glob('*retry/1_*/manifest.json')):
        run=manifest.parent;c=run/'completion.json'
        if c.exists() and json.loads(c.read_text())['status']=='success':results.append(diagnose(run))
    out=Path(__file__).resolve().parent/'results/v13_layer_gate_monitor/v12_exclusion_paths.json'
    out.write_text(json.dumps(results,indent=2)+'\n')
    for r in results:print(r['scenario'],r['seed'],r['counts'])
