#!/usr/bin/env python3
"""Plot completed legacy/clean-delta comparisons from audited report data."""
import argparse
import json
import os
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('matrix', type=Path)
    args = ap.parse_args()
    root = Path('/data1/lab409/W1lsp0').resolve()
    if not args.matrix.resolve().is_relative_to(root):
        raise ValueError('output outside user root')
    cache = root/'.ttfl_tmp/matplotlib'
    cache.mkdir(parents=True, exist_ok=True)
    os.environ['MPLCONFIGDIR'] = str(cache)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    data = json.loads((args.matrix/'trigger_delta_report.json').read_text())
    assert data['complete'] and len(data['pairs']) == 6
    fig, axes = plt.subplots(3, 3, figsize=(13, 9), sharex=True)
    metrics = [('clean_accuracy', 'Clean accuracy (%)'), ('backdoor_asr', 'Backdoor ASR (%)'),
               ('normal_exclusion_by_round', 'Honest-client exclusion (%)')]
    for i, scenario in enumerate(('none', 'backdoor', 'delayed_backdoor')):
        rows = [p for p in data['pairs'] if p['scenario'] == scenario]
        assert len(rows) == 2
        for j, (key, label) in enumerate(metrics):
            ax = axes[i, j]
            for variant, color, text in [('baseline', '#1767a3', 'Legacy'), ('candidate', '#bb5a23', 'Clean-delta')]:
                values = 100 * np.array([p[variant][key] for p in rows])
                assert values.shape == (2,30) and np.isfinite(values).all()
                x = np.arange(1,31)
                ax.plot(x,values.mean(axis=0),label=text,color=color)
                ax.fill_between(x,values.min(axis=0),values.max(axis=0),color=color,alpha=.12)
            if scenario == 'delayed_backdoor':
                ax.axvline(11,color='#555555',linestyle=':',linewidth=1)
            ax.set_title(scenario.replace('_',' ')+' — '+label,fontsize=10)
            ax.set_xlim(1,30)
            ax.set_ylim(bottom=0)
            ax.grid(alpha=.2)
            if i == 2:
                ax.set_xlabel('Federated round')
    handles,labels=axes[0,0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='lower center',ncol=2)
    fig.suptitle('Known-trigger TTFL: legacy vs clean-baseline subtraction\nLines: two-seed means; shading: seed ranges (not confidence intervals)',fontsize=13)
    fig.tight_layout(rect=(0,.05,1,.93))
    for ext in ('png','pdf'):
        out=args.matrix/f'trigger_delta_curves.{ext}'
        fig.savefig(out,dpi=180)
        print(out)
    plt.close(fig)


if __name__ == '__main__':
    main()
