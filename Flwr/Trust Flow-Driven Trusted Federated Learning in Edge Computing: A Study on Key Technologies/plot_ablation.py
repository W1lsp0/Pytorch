import os
import numpy as np
import matplotlib.pyplot as plt

# 学术排版配置
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 14,
    "axes.labelsize": 16,
    "axes.titlesize": 18,
    "legend.fontsize": 13,
    "figure.dpi": 300,
})

# 数据：根据 5.4 节及前文推演
stages = ['Stage 1 ONLY\n(TEE Gate)', 'Stage 1 + Stage 3\n(Dual-Stream)', 'Full Architecture\n(Ours)']
acc = [82.5, 88.2, 92.4]      # 准确率
asr = [75.40, 32.18, 10.21]   # 攻击成功率

x = np.arange(len(stages))
width = 0.35  # 柱子宽度

fig, ax1 = plt.subplots(figsize=(10, 6))

color_acc = '#1f77b4' # 经典蓝
bars1 = ax1.bar(x - width/2, acc, width, label='Global Accuracy (Acc. %)', color=color_acc, edgecolor='black', zorder=3)
ax1.set_ylabel('Global Accuracy (%)', color=color_acc, fontweight='bold')
ax1.tick_params(axis='y', labelcolor=color_acc)
ax1.set_ylim([0, 100])
ax1.grid(axis='y', linestyle='--', alpha=0.4, zorder=0)

# 双轴联动
ax2 = ax1.twinx()
color_asr = '#d62728' # 经典红
bars2 = ax2.bar(x + width/2, asr, width, label='Attack Success Rate (ASR %)', color=color_asr, edgecolor='black', zorder=3)
ax2.set_ylabel('Attack Success Rate (%)', color=color_asr, fontweight='bold')
ax2.tick_params(axis='y', labelcolor=color_asr)
ax2.set_ylim([0, 100])

ax1.set_xticks(x)
ax1.set_xticklabels(stages, fontweight='bold')
plt.title('Component Ablation Study: Accuracy vs Attack Mitigation')

# 在柱子上添加数值标签
def add_labels(bars, ax_obj, color):
    for bar in bars:
        height = bar.get_height()
        ax_obj.annotate(f'{height:.2f}%',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),  # 垂直偏移
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=12, color=color, fontweight='bold')

add_labels(bars1, ax1, 'black')
add_labels(bars2, ax2, 'black')

# 统一图例
lines_labels = [ax.get_legend_handles_labels() for ax in [ax1, ax2]]
lines, labels = [sum(lol, []) for lol in zip(*lines_labels)]
ax1.legend(lines, labels, loc='upper center', bbox_to_anchor=(0.5, -0.12), ncol=2)

plt.tight_layout()

cwd = os.getcwd()
pdf_path = os.path.join(cwd, 'ablation_study.pdf')
png_path = os.path.join(cwd, 'ablation_study.png')
plt.savefig(pdf_path, bbox_inches='tight')
plt.savefig(png_path, bbox_inches='tight', dpi=300)
print(f"Success: Component ablation saved to {pdf_path}")
