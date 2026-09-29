#!/usr/bin/env python3
"""Export probe-condition curves; shaded regions are ranges of two seeds."""
import argparse
import json
import os
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('matrix', type=Path)
    ap.add_argument('reference', type=Path)
    args = ap.parse_args()
    allowed = Path('/data1/lab409/W1lsp0').resolve()
    if not args.matrix.resolve().is_relative_to(allowed):
        raise ValueError('output must be under allowed root')
    cache = allowed/'.ttfl_tmp/matplotlib'
    cache.mkdir(parents=True, exist_ok=True)
    os.environ['MPLCONFIGDIR'] = str(cache)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    off = json.loads((args.reference/'long_window_report.json').read_text())['runs']
    on = json.loads((args.matrix/'probe_report.json').read_text())['runs']
    comparison = json.loads((args.matrix/'probe_condition_comparison.json').read_text())
    assert comparison['complete'] and len(comparison['validated_pairs']) == 12
    fig, axes = plt.subplots(3, 3, figsize=(13, 10), sharex=True)
    metrics = [('clean_accuracy', 'Clean accuracy (%)'), ('backdoor_asr', 'Backdoor ASR (%)'),
               ('normal_exclusion_by_round', 'Honest-client exclusion (%)')]
    for row, scenario in enumerate(('none', 'backdoor', 'delayed_backdoor')):
        for col, (metric, label) in enumerate(metrics):
            ax = axes[row, col]
            for method, color in [('single_stream', '#bb5a23'), ('ttfl', '#1767a3')]:
                for condition, runs, style in [('Off / rotation 5', off, '--'), ('On / rotation 1', on, '-')]:
                    group = [r for r in runs if r['scenario'] == scenario and r['method'] == method]
                    assert len(group) == 2
                    values = np.array([r[metric] for r in group]) * 100
                    assert values.shape == (2, 30) and np.isfinite(values).all()
                    x = np.arange(1, 31)
                    ax.plot(x, values.mean(axis=0), color=color, linestyle=style,
                            label=f'{method}: {condition}', linewidth=1.6)
                    ax.fill_between(x, values.min(axis=0), values.max(axis=0), color=color, alpha=.07)
            if scenario == 'delayed_backdoor':
                ax.axvline(11, color='#555555', linestyle=':', linewidth=1)
            ax.set_title(f'{scenario.replace("_", " ")} — {label}', fontsize=10)
            ax.set_xlim(1, 30)
            ax.set_ylim(bottom=0)
            ax.grid(alpha=.2)
            if row == 2:
                ax.set_xlabel('Federated round')
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', ncol=2, fontsize=9, bbox_to_anchor=(.5, .005))
    fig.suptitle('Known-trigger probe conditions: two development seeds\nLines: seed means; shading: seed ranges (not confidence intervals)', fontsize=13)
    fig.tight_layout(rect=(0, .07, 1, .94))
    for extension in ('png', 'pdf'):
        path = args.matrix/f'probe_condition_curves.{extension}'
        fig.savefig(path, dpi=180)
        print(path)
    plt.close(fig)


if __name__ == '__main__':
    main()
