#!/usr/bin/env python3
"""Validate matched experiments and compare probe conditions within each seed."""
import argparse
import hashlib
import json
import statistics
from pathlib import Path

from report_long_window import read_run

METHODS = ('single_stream', 'ttfl')
SCENARIOS = ('none', 'backdoor', 'delayed_backdoor')
SEEDS = (20240925, 20240926)
METRICS = ('final_accuracy', 'final_asr', 'attack_window_mean_asr',
           'normal_mean_exclusion', 'normal_ever_excluded_rate')
FIELDS = ('protocol_version', 'method', 'scenario', 'seed', 'clients', 'rounds',
          'local_epochs', 'attack_start_round', 'attack_stop_round',
          'malicious_client_ids', 'poison_rate', 'dataset', 'shared_client_pool_size',
          'server_proxy_size', 'asr_excludes_target_label', 'python')


def check_manifests(off, on):
    mismatches = [k for k in FIELDS if k not in off or k not in on or off[k] != on[k]]
    if mismatches:
        raise ValueError(f'paired protocol mismatch: {mismatches}')
    if (off['known_trigger_probe'], off['heavy_probe_rotate_mod']) != (False, 5):
        raise ValueError('expected probe off / rotation 5 reference')
    if (on['known_trigger_probe'], on['heavy_probe_rotate_mod']) != (True, 1):
        raise ValueError('expected probe on / rotation 1 intervention')


def index_runs(matrix):
    runs = {}
    for path in matrix.glob('*/manifest.json'):
        m = json.loads(path.read_text())
        if m['method'] not in METHODS:
            continue
        key = (m['scenario'], m['method'], m['seed'])
        if key in runs:
            raise ValueError(f'duplicate condition: {key}')
        runs[key] = (path.parent, m)
    return runs


def training_hash(run):
    work = run/'work'
    paths = sorted([*work.glob('*.py'), *(work/'Client').rglob('*.py'),
                    *(work/'server').rglob('*.py')])
    if not paths or not (work/'config.py').exists() or not (work/'server/server.py').exists():
        raise ValueError(f'missing training snapshot: {run}')
    h = hashlib.sha256()
    for p in paths:
        h.update(str(p.relative_to(work)).encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def artifacts(run, m, preflight=False):
    log = run if (run/'initial_model.json').exists() else run/'work/log'
    if not preflight and log != run:
        raise ValueError(f'run not archived: {run}')
    initial = json.loads((log/'initial_model.json').read_text())
    if initial['seed'] != m['seed']:
        raise ValueError(f'initial seed mismatch: {run}')
    partition = {}
    clients = []
    for name in [*(f'client_{i}' for i in range(m['clients'])), 'server_proxy']:
        d = json.loads((log/'partitions'/f'{name}.json').read_text())
        partition[name] = d
        if name != 'server_proxy':
            if d['seed'] != m['seed']:
                raise ValueError(f'partition seed mismatch: {run}/{name}')
            clients.extend(d['indices'])
    proxy = partition['server_proxy']['indices']
    if (len(clients) != 49500 or len(set(clients)) != 49500 or
            len(proxy) != m['server_proxy_size'] or len(set(proxy)) != len(proxy) or
            set(clients) & set(proxy) or set(clients) | set(proxy) != set(range(50000))):
        raise ValueError(f'partition overlap/coverage mismatch: {run}')
    h = hashlib.sha256(json.dumps(partition, sort_keys=True).encode()).hexdigest()
    return dict(training_sha256=training_hash(run), initial_sha256=initial['sha256'],
                partition_sha256=h)


def validate_pairs(reference, matrix, preflight=False):
    off, on = index_runs(reference), index_runs(matrix)
    expected = {(s, m, seed) for s in SCENARIOS for m in METHODS for seed in SEEDS}
    if set(off) != expected or not set(on) <= expected or (not preflight and set(on) != expected):
        raise ValueError('expected 12 matched conditions; final comparison requires complete matrix')
    evidence = []
    for key in sorted(on):
        off_run, off_m = off[key]
        on_run, on_m = on[key]
        check_manifests(off_m, on_m)
        a, b = artifacts(off_run, off_m), artifacts(on_run, on_m, preflight)
        if a != b:
            raise ValueError(f'training/data/initialization mismatch for {key}: {a} vs {b}')
        evidence.append(dict(scenario=key[0], method=key[1], seed=key[2],
                             reference_run=off_run.name, probe_run=on_run.name, **a))
    return evidence, off, on


def paired_delta(off, on):
    return {k: None if off[k] is None or on[k] is None else 100 * (on[k] - off[k]) for k in METRICS}


def mean_sd(values):
    if all(x is None for x in values):
        return None
    if any(x is None for x in values) or len(values) != 2:
        raise ValueError('expected two observed seed values or both not applicable')
    return dict(mean=statistics.mean(values), sd=statistics.stdev(values))


def compare_completed(matrix, reference):
    evidence, off, on = validate_pairs(reference, matrix)
    pairs = []
    for key in sorted(on):
        a, b = read_run(off[key][0]), read_run(on[key][0])
        pairs.append(dict(scenario=key[0], method=key[1], seed=key[2],
                          off_run=a['run_id'], on_run=b['run_id'],
                          delta_percentage_points=paired_delta(a, b),
                          off_c1=(a['attacker_exclusion'] or {}).get('1'),
                          on_c1=(b['attacker_exclusion'] or {}).get('1')))
    groups = []
    for s in SCENARIOS:
        for m in METHODS:
            p = [r for r in pairs if r['scenario'] == s and r['method'] == m]
            groups.append(dict(scenario=s, method=m, n=2,
                               delta_percentage_points={k: mean_sd([r['delta_percentage_points'][k] for r in p]) for k in METRICS}))
    payload = dict(complete=True, validated_pairs=evidence, pairs=pairs, groups=groups,
                   definition='probe on/rotation 1 minus probe off/rotation 5, within each seed; percentage points',
                   scope='two development seeds; combined condition change, not an isolated switch effect')
    lines = ['# 探针条件逐种子配对比较', '',
             '12 对运行的训练源码、同种子初始模型、客户端与代理集划分已校验一致。',
             '变化量 = 探针开启且每轮执行 − 探针关闭且轮换模数为 5。单位为百分点，表中为两个种子配对差值的均值 ± 样本标准差。',
             '准确率上升通常更好；ASR 和正常客户端排除率下降通常更好。两项探针配置同时改变，不能单独归因于一个开关。', '',
             '| 场景 | 方法 | 准确率变化 | 最终 ASR 变化 | 攻击窗口平均 ASR 变化 | 正常轮平均排除率变化 | 曾被排除正常客户端比例变化 |',
             '|---|---|---:|---:|---:|---:|---:|']
    for g in groups:
        vals = [g['delta_percentage_points'][k] for k in METRICS]
        cells = ['n/a' if v is None else f"{v['mean']:+.2f} ± {v['sd']:.2f}" for v in vals]
        lines.append('| ' + ' | '.join([g['scenario'], g['method'], *cells]) + ' |')
    lines += ['', 'C1 完全排除时序（聚合阻断，非 SUSPECT 检测延迟）：', '',
              '| 种子 | 场景 | 方法 | 关闭探针 | 开启探针 |', '|---|---|---|---|---|']
    for p in pairs:
        cells = []
        for k in ('off_c1', 'on_c1'):
            event = p[k]
            if event is None:
                cells.append('n/a（无攻击）')
            elif event['excluded_before_attack']:
                cells.append('攻击前已排除，不归因于检测')
            elif event['first_excluded_round_after_start'] is None:
                cells.append('30 轮内未完全排除')
            else:
                cells.append(f"第 {event['first_excluded_round_after_start']} 轮，距启动 {event['exclusion_delay_rounds']} 轮")
        lines.append('| ' + ' | '.join(map(str, [p['seed'], p['scenario'], p['method'], *cells])) + ' |')
    lines += ['', '仅两个开发种子，不作显著性结论；已知触发器条件不代表未知后门泛化。详细配对差值、阻断轮次和核验哈希保存在 JSON 中。']
    (matrix/'probe_condition_comparison.json').write_text(json.dumps(payload, indent=2, ensure_ascii=False)+'\n')
    (matrix/'probe_condition_comparison.md').write_text('\n'.join(lines)+'\n')
    return payload


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('matrix', type=Path)
    ap.add_argument('reference', type=Path)
    ap.add_argument('--preflight', action='store_true')
    args = ap.parse_args()
    if args.preflight:
        evidence, _, _ = validate_pairs(args.reference, args.matrix, preflight=True)
        payload = dict(complete=False, checked_pairs=len(evidence), expected_pairs=12,
                       purpose='partial fairness check only; no outcome comparison', pairs=evidence)
        out = args.matrix/'paired_preflight.json'
        out.write_text(json.dumps(payload, indent=2)+'\n')
        print(f'{len(evidence)}/12 pairs verified; training still pending; {out}')
    else:
        compare_completed(args.matrix, args.reference)
        print(args.matrix/'probe_condition_comparison.md')


if __name__ == '__main__':
    main()
