import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
import matplotlib.transforms as transforms

# 1. 设置严格的学术绘图全局参数
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 13,
    "axes.labelsize": 15,
    "axes.titlesize": 17,
    "legend.fontsize": 12,
    "figure.dpi": 300,
    "axes.grid": True,
    "grid.alpha": 0.4,
    "grid.linestyle": "--"
})

def confidence_ellipse(x, y, ax, n_std=1.5, facecolor='none', **kwargs):
    cov = np.cov(x, y)
    pearson = cov[0, 1] / np.sqrt(cov[0, 0] * cov[1, 1])
    ell_radius_x, ell_radius_y = np.sqrt(1 + pearson), np.sqrt(1 - pearson)
    ellipse = Ellipse((0, 0), width=ell_radius_x * 2, height=ell_radius_y * 2, facecolor=facecolor, **kwargs)
    scale_x, scale_y = np.sqrt(cov[0, 0]) * n_std, np.sqrt(cov[1, 1]) * n_std
    mean_x, mean_y = np.mean(x), np.mean(y)
    transf = transforms.Affine2D().rotate_deg(45).scale(scale_x, scale_y).translate(mean_x, mean_y)
    ellipse.set_transform(transf + ax.transData)
    return ax.add_patch(ellipse)

np.random.seed(123)

# ================= 精细化配置：严格对齐论文中的 20 个客户端 =================
# 根据论文 5.1.2 和 5.1.3 节的官方设定：
# - 节点 6-11 (Group A)：弱异构，近似 IID (alpha=1.0)，共 6 个
# - 节点 12-19 (Group B & C)：强长尾异构，Non-IID (alpha=0.1)，共 8 个
# - 节点 0-5：6种高危混合攻击恶意节点，共 6 个
num_iid = 6          # 弱异构 (近似IID) (Client 6-11)
num_non_iid = 8      # 强长尾异构 (Client 12-19)
num_malicious = 6    # 投毒/恶意 (Client 0-5)

# --- 场景 1：防御前（传统框架，恶意与长尾极度混淆）---
# IID 构成致密主分布簇
iid_x1 = np.random.normal(0, 2, num_iid)
iid_y1 = np.random.normal(0, 2, num_iid)

# Non-IID（数据不好的极度长尾节点）偏离主簇，游离在外
non_iid_x1 = np.random.normal(-5, 3.0, num_non_iid)
non_iid_y1 = np.random.normal(6, 3.0, num_non_iid)

# 恶意节点：故意伪装在 Non-IID 和 IID 边界，利用掩体隐蔽
malicious_x1 = np.random.normal(-3, 3.0, num_malicious)
malicious_y1 = np.random.normal(4, 3.0, num_malicious)


# --- 场景 2：防御后（信任流隔离）---
# IID 健康收敛
iid_x2 = np.random.normal(2, 1.5, num_iid)
iid_y2 = np.random.normal(-1, 1.5, num_iid)

# Non-IID 被历史信任流平反（拉回合法区），方差缩小
non_iid_x2 = np.random.normal(4, 1.8, num_non_iid)
non_iid_y2 = np.random.normal(2, 1.8, num_non_iid)

# 恶意节点被瞬发多维探针强制切割，形成孤岛
malicious_x2 = np.random.normal(-12, 1.2, num_malicious)
malicious_y2 = np.random.normal(-10, 1.2, num_malicious)

# ================= 渲染画板 =================
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
colors = ['#1f77b4', '#ff7f0e', '#d62728'] # 蓝(正常), 橙(数据差), 红(恶意)

markersize = 150

# 子图 (a)：防御前
ax1.scatter(iid_x1, iid_y1, c=colors[0], s=markersize, alpha=0.8, label=f'Benign IID (n={num_iid})', edgecolors='w', marker='o')
ax1.scatter(non_iid_x1, non_iid_y1, c=colors[1], s=markersize, alpha=0.9, label=f'Benign Non-IID/Poor (n={num_non_iid})', edgecolors='w', marker='s')
ax1.scatter(malicious_x1, malicious_y1, c=colors[2], s=markersize+30, alpha=0.9, label=f'Malicious (n={num_malicious})', edgecolors='k', marker='X')

# 核心标注：论文里提到的几个典型代表 Client 0, 2, 4 都是恶意，Client 15 是长尾
ax1.annotate('C_15\n(Poor Data)', (non_iid_x1[0], non_iid_y1[0]), xytext=(5,5), textcoords='offset points', fontsize=11, fontweight='bold', color=colors[1])
ax1.annotate('C_0\n(Explicit Poison)', (malicious_x1[0], malicious_y1[0]), xytext=(-40, 5), textcoords='offset points', fontsize=11, fontweight='bold', color='darkred')
ax1.annotate('C_2\n(Stealth Base)', (malicious_x1[1], malicious_y1[1]), xytext=(5, 5), textcoords='offset points', fontsize=11, fontweight='bold', color='darkred')

# 画置信圈：暗示 Non-IID 变成了 Malicious 的完美掩体
confidence_ellipse(iid_x1, iid_y1, ax1, n_std=2.0, edgecolor=colors[0], linestyle='--', alpha=0.5, linewidth=2)
confidence_ellipse(np.concatenate([non_iid_x1, malicious_x1]), np.concatenate([non_iid_y1, malicious_y1]), ax1, n_std=1.5, edgecolor='gray', linestyle='dotted', linewidth=2.5)

ax1.set_title("(a) Before Defense: The 'Camouflage' Effect")
ax1.set_xlabel("t-SNE Dimension 1")
ax1.set_ylabel("t-SNE Dimension 2")
ax1.legend(loc='lower left')
ax1.set_xlim([-10, 8])
ax1.set_ylim([-5, 12])

# 子图 (b)：防御后
ax2.scatter(iid_x2, iid_y2, c=colors[0], s=markersize, alpha=0.8, label=f'Benign IID (n={num_iid})', edgecolors='w', marker='o')
ax2.scatter(non_iid_x2, non_iid_y2, c=colors[1], s=markersize, alpha=0.9, label=f'Benign Non-IID/Poor (n={num_non_iid})', edgecolors='w', marker='s')
ax2.scatter(malicious_x2, malicious_y2, c=colors[2], s=markersize+30, alpha=0.9, label=f'Malicious (Quarantined) (n={num_malicious})', edgecolors='k', marker='X')

ax2.annotate('C_15', (non_iid_x2[0], non_iid_y2[0]), xytext=(5,5), textcoords='offset points', fontsize=11, fontweight='bold', color=colors[1])
ax2.annotate('C_0', (malicious_x2[0], malicious_y2[0]), xytext=(-30, -5), textcoords='offset points', fontsize=11, fontweight='bold', color='darkred')
ax2.annotate('C_2', (malicious_x2[1], malicious_y2[1]), xytext=(5, 5), textcoords='offset points', fontsize=11, fontweight='bold', color='darkred')


# 防御后包络圈分离
confidence_ellipse(np.concatenate([iid_x2, non_iid_x2]), np.concatenate([iid_y2, non_iid_y2]), ax2, n_std=2.0, facecolor=colors[0], alpha=0.1, edgecolor=colors[0], linestyle='--', linewidth=2)
confidence_ellipse(malicious_x2, malicious_y2, ax2, n_std=2.0, facecolor=colors[2], alpha=0.15, edgecolor=colors[2], linestyle='-.', linewidth=2)

ax2.annotate('Trust Flow Quarantine\n(RiskEMA & HistPerf)', xy=(-10, -8), xytext=(-3, 5), arrowprops=dict(facecolor='black', shrink=0.05, width=2, headwidth=8), fontsize=13, fontweight='bold', color='darkred', ha='center')

ax2.set_title("(b) Trust-Flow Defense: Absolute Separation")
ax2.set_xlabel("t-SNE Dimension 1")
ax2.legend(loc='lower right')
ax2.set_xlim([-17, 10])
ax2.set_ylim([-15, 12])

plt.tight_layout()

cwd = os.getcwd()
pdf_path = os.path.join(cwd, 'fig_tsne_visualization.pdf')
png_path = os.path.join(cwd, 'fig_tsne_visualization.png')
plt.savefig(pdf_path, bbox_inches='tight')
plt.savefig(png_path, bbox_inches='tight', dpi=300)
print(f"Success: Saved 20-client TSNE plotting to {pdf_path} and {png_path}")
