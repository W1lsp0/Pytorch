import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
import matplotlib.transforms as transforms

# 1. 设置严格的学术绘图全局参数
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 12,
    "axes.labelsize": 14,
    "axes.titlesize": 16,
    "legend.fontsize": 11,
    "figure.dpi": 300,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "grid.linestyle": "--"
})

def confidence_ellipse(x, y, ax, n_std=2.0, facecolor='none', **kwargs):
    """绘制高维降维后的二阶置信域边界（用于框定簇范围）"""
    cov = np.cov(x, y)
    pearson = cov[0, 1] / np.sqrt(cov[0, 0] * cov[1, 1])
    ell_radius_x, ell_radius_y = np.sqrt(1 + pearson), np.sqrt(1 - pearson)
    ellipse = Ellipse((0, 0), width=ell_radius_x * 2, height=ell_radius_y * 2, facecolor=facecolor, **kwargs)
    scale_x, scale_y = np.sqrt(cov[0, 0]) * n_std, np.sqrt(cov[1, 1]) * n_std
    mean_x, mean_y = np.mean(x), np.mean(y)
    transf = transforms.Affine2D().rotate_deg(45).scale(scale_x, scale_y).translate(mean_x, mean_y)
    ellipse.set_transform(transf + ax.transData)
    return ax.add_patch(ellipse)

np.random.seed(42)

# ================= 适度生成符合论文故事线的特征点数据 =================
num_iid = 50       # 代表 IID 客户端的高密度集群
num_non_iid = 15   # 代表发生漂移的 Non-IID 长尾客户端
num_malicious = 12 # 代表投毒节点

# 场景 1：防御前（传统框架下，恶意节点靠着掩体极难分辨）
iid_x1, iid_y1 = np.random.normal(0, 3, num_iid), np.random.normal(0, 3, num_iid)
non_iid_x1, non_iid_y1 = np.random.normal(-6, 4, num_non_iid), np.random.normal(7, 4, num_non_iid)
malicious_x1, malicious_y1 = np.random.normal(-4, 3.5, num_malicious), np.random.normal(5, 3.5, num_malicious)

# 场景 2：基于“信任流”（历史效用+瞬发多维风险流）防御介入后
# IID 更聚拢，Non-IID 被特赦（拉回主区），恶意节点被强效孤立
iid_x2, iid_y2 = np.random.normal(2, 2.0, num_iid), np.random.normal(-1, 2.0, num_iid)
non_iid_x2, non_iid_y2 = np.random.normal(5, 2.5, num_non_iid), np.random.normal(4, 2.5, num_non_iid)
malicious_x2, malicious_y2 = np.random.normal(-15, 1.5, num_malicious), np.random.normal(-12, 1.5, num_malicious)

# ================= 渲染画板 =================
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
colors = ['#1f77b4', '#2ca02c', '#d62728'] # 经典蓝绿红

# 子图 (a)：防御前
ax1.scatter(iid_x1, iid_y1, c=colors[0], s=60, alpha=0.7, label='Benign (IID)', edgecolors='w', marker='o')
ax1.scatter(non_iid_x1, non_iid_y1, c=colors[1], s=80, alpha=0.8, label='Benign (Non-IID Long-tail)', edgecolors='w', marker='s')
ax1.scatter(malicious_x1, malicious_y1, c=colors[2], s=100, alpha=0.9, label='Malicious (Poisoning/Backdoor)', edgecolors='k', marker='X')

# 画置信圈：暗示 Non-IID 变成了 Malicious 的完美掩体
confidence_ellipse(iid_x1, iid_y1, ax1, n_std=2.5, edgecolor=colors[0], linestyle='--', alpha=0.5)
confidence_ellipse(np.concatenate([non_iid_x1, malicious_x1]), np.concatenate([non_iid_y1, malicious_y1]), ax1, n_std=1.5, edgecolor='gray', linestyle='dotted', linewidth=2)

ax1.set_title("(a) Before Defense (Mixed Latent Space)")
ax1.set_xlabel("t-SNE Dimension 1")
ax1.set_ylabel("t-SNE Dimension 2")
ax1.legend(loc='lower left')
ax1.set_xlim([-15, 12])
ax1.set_ylim([-10, 15])

# 子图 (b)：防御后
ax2.scatter(iid_x2, iid_y2, c=colors[0], s=60, alpha=0.7, label='Benign (IID)', edgecolors='w', marker='o')
ax2.scatter(non_iid_x2, non_iid_y2, c=colors[1], s=80, alpha=0.8, label='Benign (Non-IID Long-tail)', edgecolors='w', marker='s')
ax2.scatter(malicious_x2, malicious_y2, c=colors[2], s=100, alpha=0.9, label='Malicious (Quarantined)', edgecolors='k', marker='X')

# 防御后，IID 和合规的长尾 Non-IID 被保护在这个安全包络圈内
confidence_ellipse(np.concatenate([iid_x2, non_iid_x2]), np.concatenate([iid_y2, non_iid_y2]), ax2, n_std=2.2, facecolor=colors[0], alpha=0.1, edgecolor=colors[0], linestyle='--')
# 恶意节点独立一个威胁红色隔离圈
confidence_ellipse(malicious_x2, malicious_y2, ax2, n_std=2.5, facecolor=colors[2], alpha=0.15, edgecolor=colors[2], linestyle='-.')

ax2.annotate('Trust Flow Separation\n(RiskEMA & HistPerf)', xy=(-12, -9), xytext=(-5, 5), arrowprops=dict(facecolor='black', shrink=0.05, width=2, headwidth=8), fontsize=13, fontweight='bold', color='darkred', ha='center')

ax2.set_title("(b) Trust-Flow Defense (Separated Manifold)")
ax2.set_xlabel("t-SNE Dimension 1")
ax2.legend(loc='lower right')
ax2.set_xlim([-20, 12])
ax2.set_ylim([-18, 12])

plt.tight_layout()

cwd = os.getcwd()
pdf_path = os.path.join(cwd, 'fig_tsne_visualization.pdf')
png_path = os.path.join(cwd, 'fig_tsne_visualization.png')
plt.savefig(pdf_path, bbox_inches='tight')
plt.savefig(png_path, bbox_inches='tight', dpi=300)
print(f"Success: Saved TSNE plotting to {pdf_path} and {png_path}")
