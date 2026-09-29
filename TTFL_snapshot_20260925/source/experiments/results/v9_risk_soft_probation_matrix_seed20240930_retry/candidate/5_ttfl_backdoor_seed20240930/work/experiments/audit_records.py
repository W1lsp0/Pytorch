"""Recover pre-layer blacklist exclusions only from explicit same-round evidence."""
import hashlib
import json
import re


def load_audit(run):
    raw = (run / 'round_metrics.jsonl').read_bytes()
    server = (run / 'server.log').read_bytes()
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    blocked = {}
    current = None
    for line in server.decode(errors='replace').splitlines():
        start = re.search(r'第 (\d+) 轮 \| 审计阶段开始', line)
        if start:
            current = int(start[1])
        match = re.search(r'\[Client (\d+)\] 黑名单拦截:.*?\(([^\n]*)\)', line)
        if match and current is not None:
            blocked.setdefault(current, {})[match[1]] = match[2]
        if re.search(r'第 \d+ 轮聚合完成', line):
            current = None
    repairs = []
    for row in rows:
        for cid, reason in blocked.get(row['round'], {}).items():
            stats = row['client_layer_stats']
            if cid in stats:
                if stats[cid]['included_layers'] != 0:
                    raise ValueError(f'{run}: conflicting blacklist evidence at round {row["round"]}, client {cid}')
                continue
            stats[cid] = dict(included_layers=0, excluded_layers=row['layer_count'],
                              average_clip_scale=0.0, exclusion_reason='blacklist',
                              audit_source='server.log:same_round_blacklist_interception')
            repairs.append(dict(round=row['round'], client_id=int(cid), reason=reason))
    return rows, dict(blacklist_records_recovered=repairs,
                      source_sha256={'round_metrics.jsonl': hashlib.sha256(raw).hexdigest(),
                                     'server.log': hashlib.sha256(server).hexdigest()})
