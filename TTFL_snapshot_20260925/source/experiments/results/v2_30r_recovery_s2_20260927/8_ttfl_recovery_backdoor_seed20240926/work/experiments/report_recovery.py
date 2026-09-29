#!/usr/bin/env python3
"""Report recovery separately from clients that never lost eligibility."""
import argparse
import json
import re
import statistics
from pathlib import Path

from report_long_window import read_run, pct


def recovery_event(audit, cid, start, stop):
    excluded = [r['round'] for r in audit if r['client_layer_stats'][cid]['included_layers'] == 0]
    active = [r['round'] for r in audit if r['client_layer_stats'][cid]['included_layers'] > 0]
    pre_stop = [r for r in excluded if start <= r < stop]
    after_stop = [r for r in excluded if r >= stop]
    result = dict(excluded_rounds=excluded, post_stop_excluded_rounds=after_stop,
                  first_regained_round=None, recovery_delay_from_stop=None,
                  stable_regained_round=None, relapse_rounds=[])
    if not pre_stop:
        result['status'] = 'not_excluded_during_attack'
        return result
    if stop - 1 not in excluded:
        result['status'] = 'eligible_before_attack_stopped'
        return result
    regained = next((r for r in active if r >= stop), None)
    result['status'] = 'not_recovered_in_window' if regained is None else 'recovered'
    if regained is not None:
        result.update(first_regained_round=regained, recovery_delay_from_stop=regained-stop,
                      relapse_rounds=[r for r in after_stop if r > regained])
        result['stable_regained_round'] = next((r for r in active if r >= stop and not any(x >= r for x in after_stop)), None)
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('matrix', type=Path)
    args = ap.parse_args()
    manifests = sorted(args.matrix.glob('*/manifest.json'), key=lambda p: int(p.parent.name.split('_')[0]))
    assert len(manifests) == 8, 'expected four methods and two seeds'
    rows = []
    for path in manifests:
        m = json.loads(path.read_text())
        assert m['scenario'] == 'recovery_backdoor'
        start, stop = m['attack_start_round'], m['attack_stop_round']
        assert 1 <= start < stop <= m['rounds']
        r = read_run(path.parent)
        # Independently check the attacker's actual schedule, not just env.
        log = (path.parent/'client_1.log').read_text(errors='replace')
        truth = [(int(a), b == 'True') for a,b in re.findall(r'Round (\d+) [^\n]*attack_active=(True|False)', log)]
        assert truth == [(n, start <= n < stop) for n in range(1, m['rounds']+1)], (path, 'attack schedule')
        r.update(recovery_status='evaluated', attack_stop_round_exclusive=stop,
                 post_stop_mean_asr=statistics.mean(r['backdoor_asr'][stop-1:]),
                 recovery=None)
        audit_path = path.parent/'round_metrics.jsonl'
        if audit_path.exists():
            audit = [json.loads(line) for line in audit_path.read_text().splitlines() if line.strip()]
            r['recovery'] = recovery_event(audit, '1', start, stop)
        rows.append(r)
    assert len({(r['method'],r['seed']) for r in rows}) == 8
    (args.matrix/'recovery_report.json').write_text(json.dumps(dict(runs=rows),indent=2,ensure_ascii=False))
    lines = ['# 攻击停止后的恢复开发实验', '',
             '8 项运行，每项 30 轮、20 客户端。实际攻击窗口逐轮核对 C1 日志；stop 为排他边界。', '',
             '| 种子 | 方法 | 最终准确率 | 最终 ASR | 停止后平均 ASR | C1 恢复状态 | 停止后恢复延迟 |',
             '|---|---|---:|---:|---:|---|---:|']
    labels = dict(not_excluded_during_attack='攻击期间从未完全排除', eligible_before_attack_stopped='攻击停止前已恢复资格',
                  not_recovered_in_window='窗口内未恢复', recovered='恢复过资格')
    for r in rows:
        event = r['recovery']
        status = labels[event['status']] if event else 'n/a（无逐客户端审计）'
        delay = event['recovery_delay_from_stop'] if event and event['recovery_delay_from_stop'] is not None else 'n/a'
        lines.append('| '+' | '.join(map(str,[r['seed'],r['method'],pct(r['final_accuracy']),pct(r['final_asr']),pct(r['post_stop_mean_asr']),status,delay]))+' |')
    lines += ['', '恢复延迟只对攻击停止前一轮仍为 included_layers=0 的 C1 计算，从首个干净轮 stop 到首次 included_layers>0 的轮次差；首个干净轮恢复记为 0。从未排除、停止前已恢复、窗口内未恢复分别报告，不填 0。JSON 同时保留复发轮次与持续恢复起点。', '',
              '模型残留后门消退与聚合资格恢复是不同指标。攻击停止后 ASR 下降并不单独证明恢复机制有效；本实验仅有两个开发种子。']
    (args.matrix/'recovery_report.md').write_text('\n'.join(lines)+'\n')
    print(args.matrix/'recovery_report.md')


if __name__ == '__main__':
    main()
