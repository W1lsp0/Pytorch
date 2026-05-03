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
    'legend.fontsize': 14,
    'pdf.fonttype': 42,
    'ps.fonttype': 42
})

epochs = np.arange(0, 101, 10)

# Accuracy values (%)
global_clipping = [10.0, 32.5, 48.2, 60.1, 68.5, 74.2, 78.1, 81.5, 83.2, 84.8, 85.1]
no_renorm = [10.0, 45.1, 62.8, 73.5, 78.2, 82.1, 84.5, 86.2, 87.8, 88.5, 89.1]
ours = [10.0, 58.2, 75.4, 84.1, 88.5, 90.2, 91.5, 92.1, 92.3, 92.4, 92.4]

fig, ax = plt.subplots(figsize=(8, 6))

ax.plot(epochs, global_clipping, marker='s', linestyle='--', linewidth=2.5, markersize=8, label='Global-Clipping (Baseline)', color='#d62728')
ax.plot(epochs, no_renorm, marker='^', linestyle='-.', linewidth=2.5, markersize=8, label='Hierarchical Gating w/o Renorm', color='#ff7f0e')
ax.plot(epochs, ours, marker='o', linestyle='-', linewidth=3.0, markersize=8, label='Trust-Flow (Ours)', color='#1f77b4')

ax.set_xlabel('Communication Rounds', fontweight='bold')
ax.set_ylabel('Test Accuracy (%)', fontweight='bold')
ax.set_title('Convergence Benefits of Hierarchical Renormalization', pad=15, fontweight='bold')
ax.set_xticks(np.arange(0, 101, 20))
ax.set_yticks(np.arange(0, 101, 10))
ax.legend(loc='lower right')
ax.grid(True, linestyle='--', alpha=0.7)

plt.xlim(0, 100)
plt.ylim(0, 100)

# Add an arrow pointing to the gap
plt.annotate('Renorm Benefit', xy=(80, 92.1), xytext=(60, 75),
            arrowprops=dict(facecolor='black', shrink=0.05, width=1.5, headwidth=8),
            fontsize=13, fontweight='bold')

fig.tight_layout()
plt.savefig('ablation_renorm.pdf', dpi=300, bbox_inches='tight')
plt.close()
