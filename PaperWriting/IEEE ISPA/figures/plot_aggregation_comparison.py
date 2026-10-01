"""Aggregation comparison using the supplied figure arrays unchanged.

Source: ../../Figure/plot_ablation_final.py. That source labels these arrays
"Interpolated data"; on 2026-10-01 the author explicitly confirmed measured
provenance. Raw per-run records have not been independently verified here.
Only the title and causal annotations change. No resampling or fitting occurs.
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# Set matplotlib properties for academic paper
plt.rcParams.update({
    'font.size': 14,
    'font.family': 'sans-serif',
    'axes.labelsize': 16,
    'axes.titlesize': 16,
    'xtick.labelsize': 14,
    'ytick.labelsize': 14,
    'legend.fontsize': 11,
    'pdf.fonttype': 42,
    'ps.fonttype': 42
})

# Sample every 2 rounds
epochs = np.arange(0, 51, 2)

# Interpolated data
ours = [10.0, 18.2, 28.5, 38.8, 48.5, 57.2, 64.5, 70.8, 76.2, 80.5, 84.1, 87.2, 89.5, 91.0, 91.8, 92.3, 92.4, 92.4, 92.5, 92.5, 92.5, 92.5, 92.5, 92.6, 92.6, 92.6]
no_renorm = [10.0, 16.5, 24.8, 32.5, 40.2, 47.5, 54.2, 60.5, 66.1, 71.0, 75.2, 78.8, 81.5, 83.5, 85.0, 86.2, 87.1, 87.8, 88.3, 88.7, 89.0, 89.2, 89.4, 89.5, 89.6, 89.7]
global_clipping = [10.0, 13.2, 16.8, 20.5, 24.5, 28.8, 33.2, 37.8, 42.5, 47.1, 51.5, 55.8, 59.8, 63.5, 67.1, 70.2, 72.8, 75.1, 77.0, 78.5, 79.5, 80.1, 80.5, 80.8, 81.0, 81.2]

fig, ax = plt.subplots(figsize=(8, 6))

ax.plot(epochs, global_clipping, marker='s', linestyle='--', linewidth=2.0, markersize=5, label='Global-Clipping (Baseline)', color='#d62728')
ax.plot(epochs, no_renorm, marker='^', linestyle='-.', linewidth=2.0, markersize=5, label='Hierarchical Gating w/o Renorm', color='#ff7f0e')
ax.plot(epochs, ours, marker='o', linestyle='-', linewidth=2.5, markersize=5, label='Trust-Flow (Ours)', color='#1f77b4')

ax.set_xlabel('Communication Rounds', fontweight='bold')
ax.set_ylabel('Test Accuracy (%)', fontweight='bold')
ax.set_title('Aggregation Variant Comparison', pad=15, fontweight='bold')
ax.set_xticks(np.arange(0, 51, 10))
ax.set_yticks(np.arange(0, 101, 10))
ax.legend(loc='lower right')
ax.grid(True, linestyle='--', alpha=0.7)

plt.xlim(0, 50)
plt.ylim(0, 100)

# Vertical line at round 30
ax.axvline(x=30, color='gray', linestyle=':', alpha=0.5)
ax.text(26.5, 12, 'Round 30: 92.3% Acc', fontsize=11, color='#333333', fontweight='bold', rotation=90)

fig.tight_layout()
plt.savefig(Path(__file__).with_name('fig10_ablation_renorm.pdf'), dpi=300, bbox_inches='tight')
plt.close()
