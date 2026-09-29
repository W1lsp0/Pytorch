#!/usr/bin/env python3
"""Finalize the paired independent-seed study after both matrix audits pass."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('candidate',type=Path)
    ap.add_argument('--baseline',type=Path,required=True)
    ap.add_argument('--seed',type=int,required=True)
    a=ap.parse_args()
    root=Path(__file__).resolve().parents[1]
    matrices=[a.baseline.resolve(),a.candidate.resolve()]
    assert all(p.is_relative_to(Path('/data1/lab409/W1lsp0')) for p in matrices)
    candidate=matrices[1]
    try:
        while True:
            ready=[]
            for matrix in matrices:
                done=matrix/'watcher_done.json'
                if not done.exists():
                    ready.append(False)
                    continue
                audit=json.loads((matrix/'protocol_audit.json').read_text())
                assert json.loads(done.read_text())['status']=='complete'
                assert audit['run_count']==3 and not audit['failed_runs']
                ready.append(True)
            if all(ready):
                break
            time.sleep(30)
        subprocess.run([sys.executable,str(root/'experiments/report_risk_gate_independent.py'),str(candidate),
                        '--baseline',str(matrices[0]),'--seed',str(a.seed)],check=True,cwd=root)
        subprocess.run([sys.executable,str(root/'experiments/diagnose_exclusion_paths.py'),
                        *map(str,matrices)],check=True,cwd=root)
        subprocess.run([sys.executable,str(root/'experiments/plot_risk_gate_independent.py'),str(candidate)],
                       check=True,cwd=root)
        sys.path.insert(0,str(root/'experiments'))
        from watch_matrix import active_processes
        assert not any(active_processes(matrix) for matrix in matrices)
        for matrix in matrices:
            (matrix/'controller.status').write_text('complete\n')
        payload=dict(status='complete',completed_at=time.time(),seed=a.seed,runs=6,validated_pairs=3,
                     matrices=list(map(str,matrices)),active_training_processes=[],
                     report='risk_gate_independent_report.md',plot='risk_gate_independent_curves.png',
                     interpretation='Power changes both layer admission and normalized aggregation weights; one held-out seed.')
        temp=candidate/'paired_study_done.json.tmp'
        temp.write_text(json.dumps(payload,indent=2)+'\n')
        os.replace(temp,candidate/'paired_study_done.json')
        print('Paired study complete, audited and plotted',flush=True)
    except Exception as exc:
        (candidate/'paired_study_error.json').write_text(json.dumps(dict(error=repr(exc),time=time.time()),indent=2)+'\n')
        raise

if __name__=='__main__':
    main()
