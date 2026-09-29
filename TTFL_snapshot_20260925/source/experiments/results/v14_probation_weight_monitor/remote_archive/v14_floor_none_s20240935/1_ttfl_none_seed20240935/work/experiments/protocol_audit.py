#!/usr/bin/env python3
"""Audit saved manifests, partitions, rounds and client failures."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from audit_records import load_audit

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('matrix',type=Path); args=ap.parse_args()
    failures=[]; rows=[]
    for run in sorted(p for p in args.matrix.iterdir()
                      if p.is_dir() and (p / 'manifest.json').exists()):
        manifest=json.loads((run/'manifest.json').read_text())
        completion=json.loads((run/'completion.json').read_text())
        metrics=[json.loads(x) for x in (run/'round_metrics.jsonl').read_text().splitlines() if x.strip()] if (run/'round_metrics.jsonl').exists() else []
        server=(run/'server.log').read_text(errors='replace')
        fit=[tuple(map(int,x)) for x in __import__('re').findall(r'aggregate_fit: received (\d+) results and (\d+) failures',server)]
        evaluate=[tuple(map(int,x)) for x in __import__('re').findall(r'aggregate_evaluate: received (\d+) results and (\d+) failures',server)]
        expected=manifest['rounds']; clients=manifest['clients']
        ok=completion.get('status')=='success' and len(fit)==len(evaluate)==expected and all(r==clients and f==0 for r,f in fit+evaluate)
        audit_detail = {}
        if manifest['method'] in ('ttfl', 'single_stream'):
            ok = ok and [r['round'] for r in metrics] == list(range(1, expected+1))
            repaired, provenance = load_audit(run)
            expected_ids = set(map(str, range(clients)))
            unresolved = [r['round'] for r in repaired if set(r['client_layer_stats']) != expected_ids]
            ok = ok and not unresolved
            audit_detail = dict(unresolved_client_audit_rounds=unresolved,
                                recovered_blacklist_records=len(provenance['blacklist_records_recovered']))
        rows.append({'run_id':run.name,'method':manifest['method'],'scenario':manifest['scenario'],'ok':ok,'rounds':len(fit),'fit':fit,'evaluate':evaluate,'audit_rounds':len(metrics), **audit_detail})
        if not ok: failures.append(run.name)
    out={'matrix':str(args.matrix),'run_count':len(rows),'failed_runs':failures,'runs':rows}
    (args.matrix/'protocol_audit.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)); print(json.dumps(out,indent=2,ensure_ascii=False)); raise SystemExit(1 if failures else 0)
if __name__=='__main__': main()
