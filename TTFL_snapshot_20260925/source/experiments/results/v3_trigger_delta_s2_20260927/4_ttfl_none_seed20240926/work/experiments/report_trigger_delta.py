#!/usr/bin/env python3
"""Compare the fixed clean-delta candidate against archived legacy TTFL runs."""
import argparse
import json
import math
import re
from pathlib import Path

from compare_probe_conditions import FIELDS, METRICS, artifacts, index_runs, mean_sd, paired_delta
from report_long_window import read_run


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
    args = ap.parse_args()
    reference = args.reference or args.matrix.parent/'v2_30r_probe_s2_20260927'
    old, new = index_runs(reference), index_runs(args.matrix)
    expected = {(s, 'ttfl', seed) for s in ('none', 'backdoor', 'delayed_backdoor') for seed in (20240925, 20240926)}
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
        training_hashes.add(b['training_sha256'])
        raw_audit = [json.loads(x) for x in (run/'round_metrics.jsonl').read_text().splitlines() if x.strip()]
        for row in raw_audit:
            assert row['trigger_score_mode'] == 'clean_delta'
            scores = row['trigger_score_audit']
            assert set(scores) == set(row['client_layer_stats']), (run, row['round'], 'incomplete probe evidence')
            for score in scores.values():
                assert score['mode'] == 'clean_delta'
                assert all(math.isfinite(score[k]) and 0 <= score[k] <= 1 for k in ('clean', 'raw_br', 'raw_tl', 'effective_br', 'effective_tl'))
                for corner in ('br', 'tl'):
                    assert abs(score['effective_'+corner] - max(0, score['raw_'+corner]-score['clean'])) < 1e-12
        if m['malicious_client_ids']:
            text = (run/'client_1.log').read_text(errors='replace')
            actual = [(int(n), b == 'True') for n,b in re.findall(r'Round (\d+) [^\n]*attack_active=(True|False)', text)]
            assert actual == [(n, n >= m['attack_start_round']) for n in range(1,31)]
        old_result, new_result = read_run(base), read_run(run)
        pairs.append(dict(scenario=key[0], seed=key[2], baseline=old_result, candidate=new_result,
                          delta_percentage_points=paired_delta(old_result, new_result),
                          fairness=dict(reference=a, candidate=b, planned_training_changes=changed)))
    assert len(training_hashes) == 1, 'candidate training snapshots differ'
    groups = []
    for scenario in ('none', 'backdoor', 'delayed_backdoor'):
        rows = [p for p in pairs if p['scenario'] == scenario]
        groups.append(dict(scenario=scenario, n=2,
            baseline={k:mean_sd([r['baseline'][k] for r in rows]) for k in METRICS},
            candidate={k:mean_sd([r['candidate'][k] for r in rows]) for k in METRICS},
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
    (args.matrix/'trigger_delta_report.md').write_text('\n'.join(lines)+'\n')
    print(args.matrix/'trigger_delta_report.md')


if __name__ == '__main__':
    main()
