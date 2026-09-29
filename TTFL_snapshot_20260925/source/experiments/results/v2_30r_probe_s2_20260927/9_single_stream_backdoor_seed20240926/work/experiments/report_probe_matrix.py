#!/usr/bin/env python3
"""Summarize the 30-round known-trigger-probe sensitivity matrix."""
import argparse
import csv
import json
import statistics
from pathlib import Path

from report_long_window import read_run, pct
from compare_probe_conditions import compare_completed


def mean_sd(values):
    values = [x for x in values if x is not None]
    if not values:
        return None
    return dict(mean=statistics.mean(values), sd=statistics.stdev(values) if len(values) > 1 else 0.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('matrix', type=Path)
    ap.add_argument('--reference', type=Path, help='probe-off matrix; defaults to sibling v2_30r_s2_20260927')
    args = ap.parse_args()
    manifests = sorted(args.matrix.glob('*/manifest.json'), key=lambda p: int(p.parent.name.split('_')[0]))
    expected = {(scenario, method, seed) for scenario in ('none', 'backdoor', 'delayed_backdoor')
                for method in ('single_stream', 'ttfl') for seed in (20240925, 20240926)}
    assert len(manifests) == len(expected), 'expected exactly 12 runs'
    for path in manifests:
        m = json.loads(path.read_text())
        start = 11 if m['scenario'] == 'delayed_backdoor' else 1
        required = dict(clients=20, rounds=30, local_epochs=1, dataset='CIFAR10_LOCAL',
                        attack_start_round=start, attack_stop_round=0, poison_rate=1.0,
                        known_trigger_probe=True, heavy_probe_rotate_mod=1,
                        malicious_client_ids=[] if m['scenario'] == 'none' else [1])
        assert all(m.get(k) == v for k, v in required.items()), (path, 'protocol mismatch')
    rows = [read_run(p.parent) for p in manifests]
    observed = {(r['scenario'], r['method'], r['seed']) for r in rows}
    assert observed == expected, f'matrix conditions mismatch: missing={expected-observed}, extra={observed-expected}'
    for r in rows:
        m = json.loads((args.matrix / r['run_id'] / 'manifest.json').read_text())
        assert m['known_trigger_probe'] is True and m['heavy_probe_rotate_mod'] == 1
    groups = []
    for scenario in ('none', 'backdoor', 'delayed_backdoor'):
        for method in ('single_stream', 'ttfl'):
            group = [r for r in rows if r['scenario'] == scenario and r['method'] == method]
            groups.append(dict(scenario=scenario, method=method, n=len(group),
                               final_accuracy=mean_sd([r['final_accuracy'] for r in group]),
                               final_asr=mean_sd([r['final_asr'] for r in group]),
                               attack_window_mean_asr=mean_sd([r['attack_window_mean_asr'] for r in group]),
                               normal_mean_exclusion=mean_sd([r['normal_mean_exclusion'] for r in group]),
                               normal_ever_excluded_rate=mean_sd([r['normal_ever_excluded_rate'] for r in group])))
    definitions = {
        'probe': 'known trigger probe enabled every round; rotate_mod=1',
        'scope': 'two development seeds; descriptive mean and sample SD',
        'exclusion': 'included_layers=0 among configured normal clients',
        'interpretation': 'conditional mechanism sensitivity; does not establish unknown-trigger generalization',
        'audit_reconstruction': 'zero included layers only for explicit same-round blacklist interceptions; provenance retained',
    }
    payload = dict(definitions=definitions, runs=rows, groups=groups)
    (args.matrix/'probe_report.json').write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    lines = ['# 30 轮已知触发器探针敏感性矩阵', '',
             '12 个运行；Single-Stream 与 TTFL；两个开发种子；每轮 20 个客户端。已知触发器探针每轮开启，轮换模数为 1。该结果只评价探针假设成立时的机制行为。', '',
             '| 场景 | 方法 | 最终准确率 | 最终 ASR | 攻击窗口平均 ASR | 正常客户端轮平均完全排除率 | 曾被排除正常客户端比例 |',
             '|---|---|---:|---:|---:|---:|---:|']
    for g in groups:
        def cell(key):
            v = g[key]
            return 'n/a' if v is None else f"{v['mean']*100:.2f} ± {v['sd']*100:.2f}%"
        lines.append('| ' + ' | '.join([g['scenario'], g['method'], cell('final_accuracy'), cell('final_asr'),
                                          cell('attack_window_mean_asr'), cell('normal_mean_exclusion'),
                                          cell('normal_ever_excluded_rate')]) + ' |')
    lines += ['', '逐运行 C1 完全排除情况：', '', '| 种子 | 场景 | 方法 | 首次攻击后完全排除轮 | 最终 ASR |', '|---:|---|---|---:|---:|']
    for r in rows:
        event = (r['attacker_exclusion'] or {}).get('1')
        first = event['first_excluded_round_after_start'] if event else None
        label = str(first) if first is not None else '未观测'
        if event is None:
            label = 'n/a（无攻击）'
        elif event['excluded_before_attack']:
            label += '（攻击前已排除）'
        lines.append(f"| {r['seed']} | {r['scenario']} | {r['method']} | {label} | {pct(r['final_asr'])} |")
    lines += ['', '逐层审计之前被黑名单拦截的客户端，依据同轮 server.log 明确证据计为完全排除；JSON 保留补全记录、原因和源文件哈希。未找到明确证据的缺失行会使报告失败，原始日志保持不变。']
    lines += ['', '探针开启是显式假设；本矩阵不能支持未知触发器泛化结论。首次完全排除是聚合资格指标，不等同于首次进入 SUSPECT。']
    (args.matrix/'probe_report.md').write_text('\n'.join(lines) + '\n')
    with (args.matrix/'round_curves.csv').open('w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['run_id','seed','scenario','method','round','clean_accuracy','backdoor_asr','normal_exclusion_rate'])
        for r in rows:
            for i in range(r['rounds']):
                w.writerow([r['run_id'], r['seed'], r['scenario'], r['method'], i+1,
                            r['clean_accuracy'][i], r['backdoor_asr'][i],
                            r.get('normal_exclusion_by_round', [None] * r['rounds'])[i]])
    reference = args.reference or args.matrix.parent/'v2_30r_s2_20260927'
    compare_completed(args.matrix, reference)
    print(args.matrix/'probe_report.md')
    print(args.matrix/'probe_condition_comparison.md')


if __name__ == '__main__':
    main()
