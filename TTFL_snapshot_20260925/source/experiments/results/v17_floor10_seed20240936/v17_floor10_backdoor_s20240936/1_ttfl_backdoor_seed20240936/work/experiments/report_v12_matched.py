#!/usr/bin/env python3
"""Reject mismatched conditions and report only completed V12 pairs."""
import argparse
import json
from pathlib import Path
import re
import time

from compare_probe_conditions import FIELDS, artifacts
from report_long_window import read_run

FIXED = (*FIELDS, 'known_trigger_probe', 'heavy_probe_rotate_mod',
         'trigger_score_mode', 'risk_raw_attenuation_power', 'risk_cross_channel_guard')
SWITCHES = ('risk_soft_probation', 'risk_soft_probation_reference_exclude',
            'risk_soft_probation_c2_exclude', 'risk_low_entropy_probe_guard')
METRICS = ('final_accuracy', 'final_asr', 'attack_window_mean_asr',
           'attack_window_peak_asr', 'normal_mean_exclusion', 'normal_ever_excluded_rate')


def validate_manifests(baseline, candidate):
    mismatch = [k for k in FIXED if k not in baseline or k not in candidate or baseline[k] != candidate[k]]
    if mismatch:
        raise ValueError(f'paired mismatch: {mismatch}')
    if any(baseline.get(k, False) or not candidate.get(k, False) for k in SWITCHES):
        raise ValueError('expected all four declared switches off -> on')
    expected = dict(risk_soft_probation_c2_streak=3, risk_low_entropy_probe_h=0.15,
                    risk_low_entropy_probe_acc=0.10, risk_low_entropy_probe_streak=2)
    if any(candidate.get(k) != v for k, v in expected.items()):
        raise ValueError('unexpected candidate thresholds')


def validate_schedule(run, manifest):
    for cid in manifest['malicious_client_ids']:
        content = (run / f'client_{cid}.log').read_text(errors='replace')
        observed = [(int(n), active == 'True') for n, active in re.findall(
                    r'Round (\d+) [^\n]*attack_active=(True|False)', content)]
        expected = [(n, n >= manifest['attack_start_round'] and
                    (not manifest['attack_stop_round'] or n < manifest['attack_stop_round']))
                    for n in range(1, manifest['rounds'] + 1)]
        if observed != expected:
            raise ValueError(f'attack schedule mismatch: {run}')


def state(run):
    completion = run / 'completion.json'
    if completion.exists():
        return json.loads(completion.read_text())['status']
    return 'pending'


def compare(spec):
    b, c = Path(spec['baseline']), Path(spec['candidate'])
    status = [state(p) for p in (b, c)]
    result = dict(spec, statuses=status, validation='pending')
    if status != ['success', 'success']:
        if 'failure' in status:
            result['validation'] = 'failed_run'
        return result
    bm, cm = [json.loads((p / 'manifest.json').read_text()) for p in (b, c)]
    validate_manifests(bm, cm)
    ba, ca = artifacts(b, bm), artifacts(c, cm)
    for key in ('initial_sha256', 'partition_sha256'):
        if ba[key] != ca[key]:
            raise ValueError(f'{key} differs: {spec["name"]}')
    same_source = ba['training_sha256'] == ca['training_sha256']
    if not same_source and not spec.get('historical_reference', False):
        raise ValueError(f'training source differs: {spec["name"]}')
    for run, manifest in ((b, bm), (c, cm)):
        validate_schedule(run, manifest)
    br, cr = read_run(b), read_run(c)
    result.update(validation='historical_reference' if spec.get('historical_reference') else 'validated',
        scenario=bm['scenario'], seed=bm['seed'], python=bm['python'],
        evidence=dict(baseline=ba, candidate=ca, same_training_source=same_source),
        baseline_metrics={k: br[k] for k in (*METRICS, 'attacker_exclusion')},
        candidate_metrics={k: cr[k] for k in (*METRICS, 'attacker_exclusion')},
        delta_percentage_points={k: None if br[k] is None else 100 * (cr[k] - br[k]) for k in METRICS})
    return result


def write_reports(spec_path):
    spec = json.loads(spec_path.read_text())
    rows = []
    for pair in spec['pairs']:
        try:
            rows.append(compare(pair))
        except Exception as exc:
            rows.append(dict(pair, validation='audit_failed', error=str(exc)))
    complete = all(r['validation'] in ('validated', 'historical_reference') for r in rows)
    result = dict(checked_at=time.time(), complete=complete, goal_achieved=False, pairs=rows,
        scope='Development results. Four switches change together; not a single-factor guard ablation. '
              'Historical seed 20240932 uses a different source revision. '
              'Seed 20240933 pairs must match host, Python path, training source, initialization, partitions, and attack schedule. '
              'No independent multi-seed success claim. Failed/incomplete runs excluded.')
    out = spec_path.parent
    temp = out / 'matched_report.json.tmp'
    temp.write_text(json.dumps(result, indent=2) + '\n')
    temp.replace(out / 'matched_report.json')
    lines = ['# V12 配对审计', '', result['scope'], '',
             '| 条件 | 校验 | 准确率 基线→候选 | 最终 ASR | 攻击窗口平均 ASR | 正常完全排除率 |',
             '|---|---|---:|---:|---:|---:|']
    pct = lambda v: 'n/a' if v is None else f'{100*v:.2f}%'
    for row in rows:
        if 'baseline_metrics' not in row:
            lines.append(f'| {row["name"]} | {row["validation"]} | — | — | — | — |')
            continue
        b, c = row['baseline_metrics'], row['candidate_metrics']
        cells = [pct(b[k]) + ' → ' + pct(c[k]) for k in
                 ('final_accuracy', 'final_asr', 'attack_window_mean_asr', 'normal_mean_exclusion')]
        lines.append('| ' + ' | '.join([row['name'], row['validation'], *cells]) + ' |')
    (out / 'matched_report.md').write_text('\n'.join(lines) + '\n')
    return result


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('spec', type=Path)
    args = ap.parse_args()
    r = write_reports(args.spec)
    print(json.dumps(dict(complete=r['complete'], validations={p['name']:p['validation'] for p in r['pairs']})))
