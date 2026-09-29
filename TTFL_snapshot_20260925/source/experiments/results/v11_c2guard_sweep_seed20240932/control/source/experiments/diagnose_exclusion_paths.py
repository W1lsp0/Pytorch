#!/usr/bin/env python3
"""Attribute observed full exclusions using same-round explicit isolation logs."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from audit_records import load_audit
from report_long_window import read_run


def diagnose(run):
    m = json.loads((run/'manifest.json').read_text())
    read_run(run)
    log = run/'server.log'
    isolated = {}
    current = None
    for line in log.read_text().splitlines():
        start = re.search(r'第 (\d+) 轮 \| 审计阶段开始', line)
        if start:
            current = int(start[1])
            isolated[current] = set()
        match = re.search(r'聚合隔离: 本轮排除 (\d+) .*Client IDs: ([0-9,]+)', line)
        if match:
            assert current is not None
            ids = set(map(int, match[2].split(',')))
            assert len(ids) == int(match[1])
            isolated[current] = ids
        if re.search(r'第 \d+ 轮聚合完成', line):
            current = None
    rows, provenance = load_audit(run)
    counts = Counter(honest_rounds=0, blacklist=0, isolation=0, layer_gate=0)
    records = []
    for row in rows:
        assert row['round'] in isolated
        assert len(isolated[row['round']]) == row['isolated_client_count']
        for cid, stats in row['client_layer_stats'].items():
            if int(cid) in m['malicious_client_ids']:
                continue
            counts['honest_rounds'] += 1
            if stats['included_layers']:
                continue
            reason = ('blacklist' if stats.get('exclusion_reason') == 'blacklist'
                      else 'isolation' if int(cid) in isolated[row['round']] else 'layer_gate')
            counts[reason] += 1
            records.append(dict(round=row['round'], client_id=int(cid), reason=reason))
    return dict(run=run.name, scenario=m['scenario'], seed=m['seed'], counts=dict(counts),
                records=records, source_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),
                audit_provenance=provenance)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('matrices', nargs='+', type=Path)
    args = ap.parse_args()
    for matrix in args.matrices:
        rows = [diagnose(p.parent) for p in sorted(matrix.glob('*/manifest.json'))
                if json.loads(p.read_text())['method'] == 'ttfl']
        totals = Counter()
        for row in rows:
            totals.update(row['counts'])
        payload = dict(runs=rows, totals=dict(totals),
                       limitation='Layer-gate attribution is an observed exclusion path; old logs do not store raw scores and cannot prove risk attenuation is the sole cause.')
        (matrix/'exclusion_paths.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n')
        lines = ['# 正常客户端完全排除路径', '', '同轮显式黑名单和隔离日志联合完整逐层审计分类。层门槛排除表示未明确隔离却未被任何层采纳；旧日志缺少完整 raw score，不能据此认定风险衰减是唯一原因。', '',
                 '| 运行 | 正常客户端-轮 | 黑名单 | 明确隔离 | 层门槛 |', '|---|---:|---:|---:|---:|']
        for row in rows:
            c = row['counts']
            lines.append(f"| {row['run']} | {c['honest_rounds']} | {c['blacklist']} | {c['isolation']} | {c['layer_gate']} |")
        lines += ['', f'合计：{dict(totals)}', '', '这些计数描述实际排除路径，不能单独证明风险根因。现有衰减幂消融同时改变层准入评分和归一化聚合权重，明确隔离与黑名单规则保持不变；不能把其效果全部归因于层门槛。']
        (matrix/'exclusion_paths.md').write_text('\n'.join(lines)+'\n')
        print(matrix.name,dict(totals))

if __name__ == '__main__':
    main()
