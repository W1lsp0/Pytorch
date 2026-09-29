#!/usr/bin/env python3
"""Validate and report a baseline/candidate risk-soft-probation pair."""
import argparse
from collections import Counter
import json
import math
import re
from pathlib import Path

from compare_probe_conditions import artifacts, FIELDS
from report_long_window import read_run


def read_matrix(root):
    summary = json.loads((root / 'summary.json').read_text())
    runs = {}
    for item in summary['runs']:
        run = root / item['run_id']
        manifest = json.loads((run/'manifest.json').read_text())
        if manifest['scenario'] in runs:
            raise ValueError('duplicate scenario')
        if json.loads((run/'completion.json').read_text())['status'] != 'success':
            raise ValueError(f'unsuccessful run: {run}')
        rows = [json.loads(x) for x in (run/'round_metrics.jsonl').read_text().splitlines() if x.strip()]
        if [r['round'] for r in rows] != list(range(1, manifest['rounds'] + 1)):
            raise ValueError(f'incomplete rounds: {run}')
        expected = {str(i) for i in range(manifest['clients'])}
        for row in rows:
            if set(row.get('risk_decision_audit', {})) != expected or set(row['client_layer_stats']) != expected:
                raise ValueError(f'missing audit: {run} round {row["round"]}')
            for audit in row['risk_decision_audit'].values():
                if any(not math.isfinite(v) for v in audit.values() if isinstance(v, float)):
                    raise ValueError('non-finite audit value')
                if bool(audit.get('cross_channel_guard', False)):
                    raise ValueError('unexpected cross-channel guard')
        verified = read_run(run)
        if item['clean_accuracy'] != verified['clean_accuracy'] or item['backdoor_asr'] != verified['backdoor_asr']:
            raise ValueError('summary differs from original evaluation log')
        for cid in manifest['malicious_client_ids']:
            actual = [(int(n), flag == 'True') for n, flag in re.findall(
                r'Round (\d+) [^\n]*attack_active=(True|False)',
                (run/f'client_{cid}.log').read_text())]
            expected_schedule = [(n, n >= manifest['attack_start_round'] and
                                  (not manifest['attack_stop_round'] or n < manifest['attack_stop_round']))
                                 for n in range(1, manifest['rounds'] + 1)]
            if actual != expected_schedule:
                raise ValueError(f'attack schedule mismatch: {run}')
        runs[manifest['scenario']] = (manifest, item, rows)
    return runs


def measure(manifest, summary, rows):
    malicious = {str(i) for i in manifest['malicious_client_ids']}
    normal = {str(i) for i in range(manifest['clients'])} - malicious
    normal_full, normal_explicit, malicious_isolated = [], [], []
    reasons = Counter()
    first_malicious = None
    for row in rows:
        audits = row['risk_decision_audit']
        normal_full.append(sum(row['client_layer_stats'][cid]['included_layers'] == 0 for cid in normal))
        explicit = 0
        for cid in normal:
            a = audits[cid]
            if a.get('risk_isolated') or a.get('blacklisted'):
                explicit += 1
                reasons[f'normal:{a.get("isolation_reason", "unknown")}'] += 1
        normal_explicit.append(explicit)
        if any(row['client_layer_stats'][cid]['included_layers'] == 0 for cid in malicious):
            pass
        if any(audits[cid].get('risk_isolated') or audits[cid].get('blacklisted') for cid in malicious):
            round_id = int(row['round'])
            malicious_isolated.append(round_id)
            first_malicious = round_id if first_malicious is None else first_malicious
    start = manifest['attack_start_round']
    stop = manifest['attack_stop_round'] - 1 if manifest['attack_stop_round'] else manifest['rounds']
    window = summary['backdoor_asr'][start-1:stop] if malicious else []
    total = len(rows) * len(normal)
    return dict(scenario=manifest['scenario'], seed=manifest['seed'], probation=bool(manifest['risk_soft_probation']),
                attack_window_rounds=[start, stop] if malicious else None,
                final_accuracy=float(summary['clean_accuracy'][-1]), final_asr=float(summary['backdoor_asr'][-1]),
                attack_window_mean_asr=sum(window)/len(window) if window else None,
                attack_window_peak_asr=max(window) if window else None,
                normal_excluded_total=int(sum(normal_full)), normal_client_rounds=int(total),
                normal_exclusion_rate=float(sum(normal_full)/total),
                normal_explicit_isolation_total=int(sum(normal_explicit)),
                malicious_isolated_rounds=malicious_isolated,
                first_malicious_isolation_round=first_malicious,
                reason_counts=dict(reasons))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('baseline', type=Path)
    ap.add_argument('candidate', type=Path)
    args = ap.parse_args()
    base, cand = read_matrix(args.baseline.resolve()), read_matrix(args.candidate.resolve())
    if set(base) != {'none', 'backdoor', 'delayed_backdoor'} or set(base) != set(cand):
        raise ValueError('scenario mismatch')
    report = {'complete': True, 'baseline_root': str(args.baseline.resolve()),
              'candidate_root': str(args.candidate.resolve()), 'scenarios': {},
              'scope': 'One switch: risk soft streak remains an audited/attenuated probation state; blacklist and C2 quarantine retain aggregation exclusion. Known-trigger clean_delta, one development seed.'}
    for scenario in sorted(base):
        bm, cm = base[scenario][0], cand[scenario][0]
        for field in (*FIELDS, 'known_trigger_probe', 'heavy_probe_rotate_mod',
                      'trigger_score_mode', 'risk_raw_attenuation_power', 'risk_cross_channel_guard'):
            if bm.get(field) != cm.get(field):
                raise ValueError(f'paired mismatch: {field}')
        if bool(bm.get('risk_soft_probation', False)) or not bool(cm.get('risk_soft_probation', False)):
            raise ValueError('expected baseline probation=0 and candidate probation=1')
        br, cr = args.baseline / base[scenario][1]['run_id'], args.candidate / cand[scenario][1]['run_id']
        ba, ca = artifacts(br, bm), artifacts(cr, cm)
        if ba != ca:
            raise ValueError(f'initialization/partition mismatch: {scenario}')
        b, c = measure(*base[scenario]), measure(*cand[scenario])
        report['scenarios'][scenario] = {'validation': {'baseline': ba, 'candidate': ca},
            'baseline': b, 'candidate': c,
            'delta': {k: c[k] - b[k] for k in ('final_accuracy','final_asr','normal_excluded_total','normal_exclusion_rate','normal_explicit_isolation_total')},
            'attack_window_mean_asr_delta': (c['attack_window_mean_asr'] - b['attack_window_mean_asr']) if c['attack_window_mean_asr'] is not None else None}
    out = args.candidate.resolve()
    (out/'risk_soft_probation_report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n')
    lines = ['# Risk soft probation paired report', '', report['scope'], '',
             'Normal exclusions use `included_layers=0`; explicit risk isolation is reported separately.', '']
    for scenario, item in report['scenarios'].items():
        b, c, d = item['baseline'], item['candidate'], item['delta']
        lines += [f'## {scenario}',
                  f"- final accuracy: {b['final_accuracy']:.4f} → {c['final_accuracy']:.4f} (Δ {d['final_accuracy']:+.4f})",
                  f"- final ASR: {b['final_asr']:.4f} → {c['final_asr']:.4f} (Δ {d['final_asr']:+.4f})",
                  f"- attack-window mean ASR: {b['attack_window_mean_asr']} → {c['attack_window_mean_asr']} (Δ {item['attack_window_mean_asr_delta']})",
                  f"- normal exclusions: {b['normal_excluded_total']}/{b['normal_client_rounds']} → {c['normal_excluded_total']}/{c['normal_client_rounds']} (rate Δ {d['normal_exclusion_rate']:+.4%})",
                  f"- explicit normal isolation: {b['normal_explicit_isolation_total']} → {c['normal_explicit_isolation_total']}",
                  f"- malicious isolated rounds: {b['malicious_isolated_rounds']} → {c['malicious_isolated_rounds']}",
                  f"- reasons baseline: `{json.dumps(b['reason_counts'], ensure_ascii=False)}`",
                  f"- reasons candidate: `{json.dumps(c['reason_counts'], ensure_ascii=False)}`", '']
    (out/'risk_soft_probation_report.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(out/'risk_soft_probation_report.md')


if __name__ == '__main__':
    main()
