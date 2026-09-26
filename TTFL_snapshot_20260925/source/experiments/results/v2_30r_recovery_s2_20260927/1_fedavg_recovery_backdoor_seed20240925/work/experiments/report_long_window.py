#!/usr/bin/env python3
"""Strict, reproducible audit and report of a completed development matrix."""
import argparse
import csv
import json
import re
import statistics
from pathlib import Path

from summarize_matrix import pairs


def read_run(run):
    m = json.loads((run / 'manifest.json').read_text())
    completion = json.loads((run / 'completion.json').read_text())
    assert completion['status'] == 'success', run
    text = (run / 'server.log').read_text(errors='replace')
    for phase in ('fit', 'evaluate'):
        counts = re.findall(r'aggregate_' + phase + r': received (\d+) results and (\d+) failures', text)
        assert len(counts) == m['rounds'], (run, phase, len(counts))
        assert all(int(n) == m['clients'] and int(f) == 0 for n, f in counts), (run, phase)
    acc, asr = pairs(text, 'accuracy'), pairs(text, 'asr_backdoor')
    assert len(acc) == len(asr) == m['rounds'], (run, 'evaluation history')
    attacked = bool(m['malicious_client_ids'])
    start = m['attack_start_round']
    stop = m['attack_stop_round'] or m['rounds']
    window = asr[start - 1:stop] if attacked else []
    result = dict(run_id=run.name, method=m['method'], scenario=m['scenario'], seed=m['seed'],
                  rounds=m['rounds'], final_accuracy=acc[-1], final_asr=asr[-1],
                  attack_window_mean_asr=statistics.mean(window) if window else None,
                  attack_window_peak_asr=max(window) if window else None,
                  attack_start_round=start if attacked else None,
                  recovery_status='not_measured_no_attack_stop' if attacked else 'not_applicable',
                  normal_final_exclusion=None, normal_mean_exclusion=None,
                  normal_ever_excluded_ids=None, normal_ever_excluded_rate=None,
                  attacker_exclusion=None, clean_accuracy=acc, backdoor_asr=asr)
    audit_path = run / 'round_metrics.jsonl'
    if m['method'] in ('single_stream', 'ttfl'):
        audit = [json.loads(line) for line in audit_path.read_text().splitlines() if line.strip()]
        assert [r['round'] for r in audit] == list(range(1, m['rounds'] + 1)), run
        all_ids = {str(i) for i in range(m['clients'])}
        bad_ids = {str(i) for i in m['malicious_client_ids']}
        normal_ids = all_ids - bad_ids
        excluded, partial = [], []
        for r in audit:
            stats = r['client_layer_stats']
            assert set(stats) == all_ids, (run, r['round'], 'missing client audit')
            excluded.append({cid for cid in normal_ids if stats[cid]['included_layers'] == 0})
            partial.append({cid for cid in normal_ids if 0 < stats[cid]['included_layers'] < r['layer_count']})
        rates = [len(ids) / len(normal_ids) for ids in excluded]
        ever = set().union(*excluded)
        result.update(normal_final_exclusion=rates[-1], normal_mean_exclusion=statistics.mean(rates),
                      normal_ever_excluded_ids=sorted(map(int, ever)), normal_ever_excluded_rate=len(ever)/len(normal_ids),
                      normal_exclusion_by_round=rates,
                      normal_partial_exclusion_by_round=[len(ids)/len(normal_ids) for ids in partial])
        result['attacker_exclusion'] = {}
        for cid in sorted(bad_ids):
            blocked = [r['round'] for r in audit if r['client_layer_stats'][cid]['included_layers'] == 0]
            preblocked = any(r < start for r in blocked)
            first = next((r for r in blocked if r >= start), None)
            result['attacker_exclusion'][cid] = dict(
                excluded_rounds=blocked, excluded_before_attack=preblocked,
                first_excluded_round_after_start=first,
                exclusion_delay_rounds=first-start if first is not None and not preblocked else None,
                status='pre_attack_exclusion' if preblocked else ('observed' if first is not None else 'not_observed'),
                observed_attack_rounds=m['rounds']-start+1)
    return result


def pct(x):
    return 'n/a' if x is None else f'{100*x:.2f}%'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('matrix', type=Path)
    parser.add_argument('--expected-runs', type=int, default=24)
    args = parser.parse_args()
    manifests = sorted(args.matrix.glob('*/manifest.json'), key=lambda p: int(p.parent.name.split('_')[0]))
    assert len(manifests) == args.expected_runs, 'incomplete matrix'
    rows = [read_run(p.parent) for p in manifests]
    assert len({(r['method'], r['scenario'], r['seed']) for r in rows}) == len(rows), 'duplicate conditions'
    definitions = {
        'normal_clients': 'IDs excluding configured attackers for all rounds, including pre-attack rounds',
        'normal_mean_exclusion': 'fully excluded honest client-rounds / all honest client-rounds',
        'normal_ever_excluded_rate': 'unique honest clients fully excluded at least once / honest clients',
        'exclusion_delay_rounds': 'first post-start round with zero included layers minus attack start; not a SUSPECT detection delay',
        'pre_attack_exclusion': 'reported separately; cannot attribute pre-existing exclusion to attack detection',
        'recovery': 'not measured: these runs do not stop the attack',
        'baseline_audit': 'n/a means per-client layer eligibility is unavailable, not zero exclusion',
        'scope': 'two development seeds; descriptive sample mean and SD, not significance or final paper evidence',
    }
    groups = []
    for scenario in ('none', 'backdoor', 'delayed_backdoor'):
        for method in ('fedavg', 'fltrust', 'single_stream', 'ttfl'):
            group = [r for r in rows if r['scenario'] == scenario and r['method'] == method]
            assert len(group) == 2, (scenario, method, 'expected two seeds')
            g = dict(scenario=scenario, method=method, n=len(group))
            for key in ('final_accuracy', 'final_asr', 'attack_window_mean_asr', 'normal_mean_exclusion', 'normal_ever_excluded_rate'):
                values = [r[key] for r in group if r[key] is not None]
                g[key] = dict(mean=statistics.mean(values), sd=statistics.stdev(values)) if len(values) == 2 else None
            groups.append(g)
    (args.matrix/'long_window_report.json').write_text(json.dumps(dict(definitions=definitions, runs=rows, groups=groups), indent=2, ensure_ascii=False))
    lines = ['# 30 轮开发矩阵汇总', '', '24 个运行；2 个开发种子；每轮 20 个客户端；本地 CIFAR-10。全部 fit/evaluate 轮次完整且 0 failures。',
             '', '持续后门从第 1 轮开始，延迟后门从第 11 轮开始；投毒比例 1.0，已知触发器探针关闭。以下为两种子的均值 ± 样本标准差，仅作开发分析。', '',
             '| 场景 | 方法 | 最终准确率 | 最终 ASR | 攻击窗口平均 ASR | 正常客户端轮平均排除率 | 曾被完全排除的正常客户端比例 |',
             '|---|---|---:|---:|---:|---:|---:|']
    for g in groups:
        vals = [g[k] for k in ('final_accuracy','final_asr','attack_window_mean_asr','normal_mean_exclusion','normal_ever_excluded_rate')]
        cells = ['n/a' if v is None else f"{v['mean']*100:.2f} ± {v['sd']*100:.2f}%" for v in vals]
        lines.append('| ' + ' | '.join([g['scenario'], g['method'], *cells]) + ' |')
    lines += ['', '## 每次运行', '', '| 种子 | 场景 | 方法 | 准确率 | 最终 ASR | 正常客户端最终排除率 | 曾被排除的正常 ID | C1 首次完全排除（攻击启动后） |', '|---|---|---|---:|---:|---:|---|---|']
    for r in rows:
        event = (r['attacker_exclusion'] or {}).get('1')
        if event is None:
            label = 'n/a'
        elif event['status'] == 'pre_attack_exclusion':
            label = f"{event['first_excluded_round_after_start']}（攻击前已被排除，不计检测延迟）"
        elif event['status'] == 'not_observed':
            label = '30 轮内未观测到'
        else:
            label = f"{event['first_excluded_round_after_start']}（延迟 {event['exclusion_delay_rounds']} 轮）"
        lines.append('| ' + ' | '.join(map(str,[r['seed'],r['scenario'],r['method'],pct(r['final_accuracy']),pct(r['final_asr']),pct(r['normal_final_exclusion']),r['normal_ever_excluded_ids'] if r['normal_ever_excluded_ids'] is not None else 'n/a',label])) + ' |')
    lines += ['', '指标说明：完全排除指 included_layers=0；隔离状态与实际聚合资格分别对待。轮平均排除率统计正常客户端-轮，累计比例统计至少一次完全排除的不同正常客户端，不能相加。n/a 表示没有对应审计。', '',
              '本批次没有攻击停止窗口，不能报告恢复时间。首次完全排除衡量聚合阻断，不等同于首次 SUSPECT 状态。两种子开发结果不能证明统计显著性或未知后门泛化。', '',
              '第 6–9 项的调度父进程曾退出，其完成状态由完整训练/评估日志恢复；原子进程退出码未被原调度器归档。']
    (args.matrix/'long_window_report.md').write_text('\n'.join(lines)+'\n')
    with (args.matrix/'round_curves.csv').open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['run_id','seed','scenario','method','round','clean_accuracy','backdoor_asr','normal_exclusion_rate'])
        for r in rows:
            for i in range(r['rounds']):
                writer.writerow([r['run_id'],r['seed'],r['scenario'],r['method'],i+1,r['clean_accuracy'][i],r['backdoor_asr'][i],r.get('normal_exclusion_by_round',[None]*r['rounds'])[i]])
    print(args.matrix/'long_window_report.md')


if __name__ == '__main__':
    main()
