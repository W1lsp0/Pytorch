#!/usr/bin/env python3
"""Describe observed honest-client exclusion by partition; do not infer causes."""
import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

from audit_records import load_audit
from report_long_window import read_run


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('probe', type=Path)
    ap.add_argument('reference', type=Path)
    args = ap.parse_args()
    records = []
    provenance = []
    for condition, matrix in [('off', args.reference), ('on', args.probe)]:
        for path in matrix.glob('*/manifest.json'):
            m = json.loads(path.read_text())
            if m['method'] not in ('single_stream', 'ttfl'):
                continue
            run = path.parent
            read_run(run)  # Completion, round counts, and full client audit.
            audit, evidence = load_audit(run)
            provenance.append(dict(run=str(run), **evidence['source_sha256']))
            events = {}
            for e in evidence['blacklist_records_recovered']:
                events.setdefault(e['client_id'], e)
            probe_values = {}
            current = None
            for line in (run/'server.log').read_text(errors='replace').splitlines():
                start = re.search(r'第 (\d+) 轮 \| 审计阶段开始', line)
                if start:
                    current = int(start[1])
                match = re.search(r'\[Client (\d+)\] Scheme K .*TrigBR: ([\d.]+) \| TrigTL: ([\d.]+)', line)
                if match and current:
                    probe_values[(int(match[1]), current)] = (float(match[2]), float(match[3]))
            for cid in range(m['clients']):
                if cid in m['malicious_client_ids']:
                    continue
                part = json.loads((run/f'partitions/client_{cid}.json').read_text())
                excluded = [r['round'] for r in audit if r['client_layer_stats'][str(cid)]['included_layers'] == 0]
                blocked = [r['round'] for r in audit if r['client_layer_stats'][str(cid)].get('exclusion_reason') == 'blacklist']
                event = events.get(cid)
                first = excluded[0] if excluded else None
                scores = probe_values.get((cid, first))
                records.append(dict(condition=condition, run_id=run.name, method=m['method'],
                                    scenario=m['scenario'], seed=m['seed'], client_id=cid, group=part['group'],
                                    target_fraction=part['class_counts'][0]/len(part['indices']), rounds=m['rounds'],
                                    excluded_rounds=len(excluded), blacklist_intercepted_rounds=len(blocked),
                                    first_excluded_round=first,
                                    first_observed_blacklist_round=event['round'] if event else None,
                                    blacklist_reason=event['reason'] if event else None,
                                    raw_br_at_first_exclusion=scores[0] if scores else None,
                                    raw_tl_at_first_exclusion=scores[1] if scores else None))
    groups = []
    for condition in ('off', 'on'):
        for method in ('single_stream', 'ttfl'):
            for group in ('iid', 'moderate', 'extreme'):
                rows = [r for r in records if (r['condition'], r['method'], r['group']) == (condition, method, group)]
                groups.append(dict(condition=condition, method=method, group=group,
                                   honest_run_clients=len(rows), client_rounds=sum(r['rounds'] for r in rows),
                                   exclusion_rate=sum(r['excluded_rounds'] for r in rows)/sum(r['rounds'] for r in rows),
                                   intercepted_run_clients=sum(r['first_observed_blacklist_round'] is not None for r in rows),
                                   blacklist_client_rounds=sum(r['blacklist_intercepted_rounds'] for r in rows)))
    reasons = Counter(r['blacklist_reason'] for r in records if r['condition'] == 'on' and r['blacklist_reason'])
    out = args.probe
    (out/'honest_exclusion_diagnosis.json').write_text(json.dumps(dict(groups=groups, clients=records,
        probe_on_blacklist_reasons=dict(reasons), provenance=provenance), indent=2, ensure_ascii=False)+'\n')
    with (out/'honest_exclusion_clients.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(records[0]))
        w.writeheader(); w.writerows(records)
    lines = ['# 正常客户端误排除诊断', '',
             '合并三个场景和两个开发种子；每次运行分别按配置剔除攻击客户端。run-client 为一次运行中的一个客户端，不是独立受试者。分组采用保存的真实划分标签，不使用客户端自报熵。', '',
             '| 探针条件 | 方法 | 分片组 | 正常 run-client 数 | 完全排除客户端-轮比例 | 观测到黑名单拦截的 run-client 数 | 黑名单拦截客户端-轮数 |',
             '|---|---|---|---:|---:|---:|---:|']
    for g in groups:
        lines.append(f"| {g['condition']} | {g['method']} | {g['group']} | {g['honest_run_clients']} | {100*g['exclusion_rate']:.2f}% | {g['intercepted_run_clients']} | {g['blacklist_client_rounds']} |")
    lines += ['', '开启探针时正常 run-client 的首次黑名单拦截原因计数：', '']
    lines += [f'- {key}: {value}' for key,value in sorted(reasons.items())]
    lines += ['', '首次黑名单拦截通常晚于作出封禁决定的轮次，不能把两者混为一谈。未到下一轮即结束的封禁也可能不在该计数中。', '',
              '代码审查线索：原始触发器分数是补丁图片的目标类概率和命中率加权和（0.7/0.3），没有干净图片的同模型对照。无攻击也可能因目标类偏好被评为异常；旧日志没有干净目标类分数，因此这只是待检验机制解释。',
              '下一项候选：以同一批图片、同一客户端模型上的正向分数增量 max(0, patched_score - clean_score) 代替原始分数，保持其他风险和封禁阈值不变。SVD 仍按旧实现取最后一次左上补丁前向特征，单独标为后续消融问题；本次不同时调整它。']
    (out/'honest_exclusion_diagnosis.md').write_text('\n'.join(lines)+'\n')
    print(out/'honest_exclusion_diagnosis.md')


if __name__ == '__main__':
    main()
