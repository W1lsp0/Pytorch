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

attacks = ['Sign-Flipping\n(Untargeted)', 'Gradient Scaling\n(Untargeted)', 'Clean-Label Backdoor\n(Targeted)']

# ASR values (%)
vanilla_root = [12.5, 24.3, 42.1]
shallow_probes = [8.1, 11.2, 28.5]
full_probes = [4.2, 3.8, 9.2]

x = np.arange(len(attacks))
width = 0.25

fig, ax = plt.subplots(figsize=(8, 6))

rects1 = ax.bar(x - width, vanilla_root, width, label='Vanilla Clean-Root (No Probes)', color='#d62728', alpha=0.8, edgecolor='black', hatch='//')
rects2 = ax.bar(x, shallow_probes, width, label='+ Shallow Probes ($r_{grad}$)', color='#ff7f0e', alpha=0.8, edgecolor='black', hatch='\\\\')
rects3 = ax.bar(x + width, full_probes, width, label='+ Full Probes (Ours)', color='#2ca02c', alpha=0.9, edgecolor='black')

ax.set_ylabel('Attack Success Rate (ASR) %', fontweight='bold')
ax.set_title('Ablation on Multi-dimensional Risk Probes', pad=15, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(attacks, fontweight='bold')
ax.legend(loc='upper left')
ax.grid(axis='y', linestyle='--', alpha=0.7)

# Add values on top of bars
def autolabel(rects):
    for rect in rects:
        height = rect.get_height()
        ax.annotate(f'{height:.1f}%',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=12)

autolabel(rects1)
autolabel(rects2)
autolabel(rects3)

plt.ylim(0, 50)
fig.tight_layout()
plt.savefig('ablation_probes.pdf', dpi=300, bbox_inches='tight')
plt.close()
