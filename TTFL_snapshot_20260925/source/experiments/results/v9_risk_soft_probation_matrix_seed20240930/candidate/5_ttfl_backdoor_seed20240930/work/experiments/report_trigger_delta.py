#!/usr/bin/env python3
"""Compare the fixed clean-delta candidate against archived legacy TTFL runs."""
import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path

from compare_probe_conditions import FIELDS, METRICS, artifacts, index_runs, mean_sd, paired_delta
from report_long_window import read_run


def validate_scores(row):
    assert row['trigger_score_mode'] == 'clean_delta'
    scores = row['trigger_score_audit']
    assert set(scores) == set(row['client_layer_stats']), (row['round'], 'incomplete probe evidence')
    for score in scores.values():
        assert score['mode'] == 'clean_delta'
        assert all(math.isfinite(score[k]) and 0 <= score[k] <= 1
                   for k in ('clean', 'raw_br', 'raw_tl', 'effective_br', 'effective_tl'))
        for corner in ('br', 'tl'):
            assert abs(score['effective_'+corner] - max(0, score['raw_'+corner]-score['clean'])) < 1e-12
    return len(scores)


def validate_frozen_source(run, protocol):
    for name, expected in protocol['source_files'].items():
        actual = hashlib.sha256((run/'work'/name).read_bytes()).hexdigest()
        assert actual == expected, (run, name, 'source differs from frozen protocol')


def enrich_result(run, manifest):
    result = read_run(run)
    normal_ids = set(range(manifest['clients'])) - set(manifest['malicious_client_ids'])
    restored = result['audit_provenance']['blacklist_records_recovered']
    ids = sorted({r['client_id'] for r in restored if r['client_id'] in normal_ids})
    result['normal_blacklist_intercepted_ids'] = ids
    result['normal_blacklist_intercepted_rate'] = len(ids)/len(normal_ids)
    completion = json.loads((run/'completion.json').read_text())
    result['elapsed_seconds'] = completion.get('elapsed_seconds',
        (completion.get('original_completion') or {}).get('elapsed_seconds'))
    result['recovered_after_launcher_exit'] = completion.get('recovered_after_launcher_exit', False)
    return result


def source_changes(reference, candidate):
    def files(run):
        root = run/'work'
        paths = [*root.glob('*.py'), *(root/'Client').rglob('*.py'), *(root/'server').rglob('*.py')]
        return {str(p.relative_to(root)): p.read_bytes() for p in paths}
    a, b = files(reference), files(candidate)
    changed = sorted(k for k in a.keys() | b.keys() if a.get(k) != b.get(k))
    if set(changed) != {'server/strategy.py', 'server/probe_scoring.py'}:
        raise ValueError(f'unplanned training changes: {changed}')
    return changed


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('matrix', type=Path)
    ap.add_argument('--reference', type=Path)
    ap.add_argument('--preflight', action='store_true', help='validate available snapshots and complete audit rows, not outcomes')
    args = ap.parse_args()
    reference = args.reference or args.matrix.parent/'v2_30r_probe_s2_20260927'
    old, new = index_runs(reference), index_runs(args.matrix)
    expected = {(s, 'ttfl', seed) for s in ('none', 'backdoor', 'delayed_backdoor') for seed in (20240925, 20240926)}
    protocol = json.loads((args.matrix/'frozen_protocol.json').read_text())
    if args.preflight:
        assert set(new) <= expected and expected <= old.keys()
        evidence = []
        for key in sorted(new):
            base, bm = old[key]
            run, m = new[key]
            assert all(bm[k] == m[k] for k in FIELDS), (run, 'protocol mismatch')
            assert m['trigger_score_mode'] == 'clean_delta' and m['known_trigger_probe']
            assert m['heavy_probe_rotate_mod'] == bm['heavy_probe_rotate_mod'] == 1
            validate_frozen_source(run, protocol)
            changes = source_changes(base, run)
            a, b = artifacts(base, bm), artifacts(run, m, preflight=True)
            assert all(a[k] == b[k] for k in ('initial_sha256', 'partition_sha256'))
            path = run/'work/log/round_metrics.jsonl'
            # The final line can still be in progress in a live append-only log.
            lines = path.read_bytes().splitlines(keepends=True) if path.exists() else []
            rows = [json.loads(line) for line in lines if line.endswith(b'\n') and line.strip()]
            count = sum(validate_scores(row) for row in rows)
            evidence.append(dict(run_id=run.name, audit_rounds=len(rows), validated_client_scores=count,
                                 reference=a, candidate=b, planned_training_changes=changes))
        payload = dict(complete=False, checked_runs=len(evidence), expected_runs=6,
                       purpose='live protocol and scoring verification only; no efficacy conclusions', runs=evidence)
        (args.matrix/'trigger_delta_preflight.json').write_text(json.dumps(payload,indent=2)+'\n')
        print(f'Preflight: {len(evidence)}/6 snapshots, {sum(r["validated_client_scores"] for r in evidence)} client-score records verified')
        return
    assert set(new) == expected and expected <= old.keys(), 'expected six completed paired TTFL conditions'
    pairs = []
    training_hashes = set()
    for key in sorted(new):
        base, bm = old[key]
        run, m = new[key]
        assert all(bm[k] == m[k] for k in FIELDS), (run, 'protocol mismatch')
        assert (m['rounds'], m['clients'], m['local_epochs']) == (30, 20, 1)
        assert bm.get('trigger_score_mode', 'legacy') == 'legacy'
        assert m['trigger_score_mode'] == 'clean_delta'
        assert m['known_trigger_probe'] and bm['known_trigger_probe']
        assert m['heavy_probe_rotate_mod'] == bm['heavy_probe_rotate_mod'] == 1
        a, b = artifacts(base, bm), artifacts(run, m)
        assert all(a[k] == b[k] for k in ('initial_sha256', 'partition_sha256'))
        changed = source_changes(base, run)
        validate_frozen_source(run, protocol)
        training_hashes.add(b['training_sha256'])
        raw_audit = [json.loads(x) for x in (run/'round_metrics.jsonl').read_text().splitlines() if x.strip()]
        for row in raw_audit:
            validate_scores(row)
        if m['malicious_client_ids']:
            text = (run/'client_1.log').read_text(errors='replace')
            actual = [(int(n), b == 'True') for n,b in re.findall(r'Round (\d+) [^\n]*attack_active=(True|False)', text)]
            assert actual == [(n, n >= m['attack_start_round']) for n in range(1,31)]
        old_result, new_result = enrich_result(base, bm), enrich_result(run, m)
        new_result['additional_clean_forwards'] = sum(len(row['trigger_score_audit']) for row in raw_audit)
        pairs.append(dict(scenario=key[0], seed=key[2], baseline=old_result, candidate=new_result,
                          delta_percentage_points=paired_delta(old_result, new_result),
                          fairness=dict(reference=a, candidate=b, planned_training_changes=changed)))
    assert len(training_hashes) == 1, 'candidate training snapshots differ'
    report_metrics = (*METRICS, 'attack_window_peak_asr', 'normal_blacklist_intercepted_rate')
    groups = []
    for scenario in ('none', 'backdoor', 'delayed_backdoor'):
        rows = [p for p in pairs if p['scenario'] == scenario]
        groups.append(dict(scenario=scenario, n=2,
            baseline={k:mean_sd([r['baseline'][k] for r in rows]) for k in report_metrics},
            candidate={k:mean_sd([r['candidate'][k] for r in rows]) for k in report_metrics},
            delta_percentage_points={k:mean_sd([r['delta_percentage_points'][k] for r in rows]) for k in METRICS}))
    payload = dict(complete=True, pairs=pairs, groups=groups,
                   definition='clean_delta = max(0, patched target affinity - clean target affinity); other risk thresholds unchanged',
                   limitations='development seeds and known trigger only; requires one additional clean forward per probed client; legacy SVD source retained')
    (args.matrix/'trigger_delta_report.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n')
    lines = ['# 干净基线差分触发器评分开发对照', '',
             '6 项候选运行配对已归档 TTFL 已知触发器结果。初始化和划分相同，仅改变触发器评分并增加审计；风险阈值、永久封禁和 SVD 特征来源保持不变。',
             '每个候选客户端探针比旧实现多一次干净图片前向，耗时不可直接视为相同预算。两个种子为已使用的开发种子，不作独立验证或显著性结论。', '',
             '| 场景 | 旧/新最终准确率 | 旧/新最终 ASR | 旧/新攻击窗口 ASR | 旧/新正常轮平均排除率 | 排除率变化（百分点） |',
             '|---|---:|---:|---:|---:|---:|']
    for g in groups:
        cells = []
        for k in ('final_accuracy', 'final_asr', 'attack_window_mean_asr', 'normal_mean_exclusion'):
            a,b = g['baseline'][k],g['candidate'][k]
            cells.append('n/a' if a is None else f"{a['mean']*100:.2f}% / {b['mean']*100:.2f}%")
        d=g['delta_percentage_points']['normal_mean_exclusion']
        lines.append('| '+' | '.join([g['scenario'],*cells,f"{d['mean']:+.2f} ± {d['sd']:.2f}"])+' |')
    lines += ['', 'JSON 保留全部逐运行指标、C1 阻断轮次、正常客户端排除 ID、源日志证据与配对差值。候选是否改善误伤，必须同时检查攻击窗口 ASR、最终准确率及两个种子的一致性。']
    lines += ['', '| 场景 | 旧/新攻击窗口峰值 ASR | 旧/新正常客户端黑名单拦截比例 |', '|---|---:|---:|']
    for g in groups:
        cells = []
        for k in ('attack_window_peak_asr', 'normal_blacklist_intercepted_rate'):
            a, b = g['baseline'][k], g['candidate'][k]
            cells.append('n/a' if a is None else f"{100*a['mean']:.2f}% / {100*b['mean']:.2f}%")
        lines.append('| '+' | '.join([g['scenario'],*cells])+' |')
    lines += ['', '黑名单拦截比例统计正常客户端中至少在一轮被明确拦截者，不包含仅在最后一轮作出而未观测到后续拦截的封禁。耗时为并发环境中的运行墙钟时间，不能当作独立硬件基准。', '',
              '| 种子 | 场景 | 旧/新运行秒数 | 新增干净图片前向次数 |', '|---|---|---:|---:|']
    for p in pairs:
        values = [p[k]['elapsed_seconds'] for k in ('baseline','candidate')]
        times = ' / '.join('n/a' if v is None else f'{v:.1f}' for v in values)
        lines.append(f"| {p['seed']} | {p['scenario']} | {times} | {p['candidate']['additional_clean_forwards']} |")
    with (args.matrix/'trigger_delta_round_curves.csv').open('w',newline='') as f:
        w = csv.writer(f)
        w.writerow(['scenario','seed','variant','round','clean_accuracy','backdoor_asr','normal_exclusion_rate'])
        for p in pairs:
            for variant in ('baseline','candidate'):
                r = p[variant]
                for i in range(r['rounds']):
                    w.writerow([p['scenario'],p['seed'],variant,i+1,r['clean_accuracy'][i],r['backdoor_asr'][i],r['normal_exclusion_by_round'][i]])
    (args.matrix/'trigger_delta_report.md').write_text('\n'.join(lines)+'\n')
    print(args.matrix/'trigger_delta_report.md')


if __name__ == '__main__':
    main()
