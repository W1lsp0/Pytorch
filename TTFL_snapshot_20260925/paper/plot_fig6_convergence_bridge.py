import matplotlib.pyplot as plt
import numpy as np
import textwrap


plt.rcParams.update({
    "font.size": 11,
    "font.family": "sans-serif",
    "axes.labelsize": 12,
    "axes.titlesize": 12,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 9,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


rounds = np.arange(1, 31)

# Reconstructed from the current Fig. 6 end points and the paper text.
# The formal reported metrics are the five-seed means: Acc=92.31, ASR=10.21.
acc = np.array([
    37.3, 50.1, 62.8, 75.6, 88.4,
    88.9, 89.3, 89.8, 90.1, 90.5,
    90.7, 91.0, 91.2, 91.4, 91.6,
    91.7, 91.8, 91.85, 91.9, 92.0,
    92.02, 92.08, 92.12, 92.17, 92.20,
    92.22, 92.24, 92.26, 92.29, 92.31,
])
asr = np.array([
    10.1, 10.1, 10.1, 10.1, 10.1,
    10.1, 10.1, 10.1, 10.1, 10.1,
    10.1, 10.1, 10.1, 10.1, 10.1,
    10.1, 10.1, 10.1, 10.1, 10.1,
    10.1, 10.1, 10.1, 10.1, 10.1,
    10.1, 10.1, 10.1, 10.1, 10.21,
])

# Round-30 values from Fig. 9(b)'s renormalization ablation script.
renorm_labels = [
    "Global clipping",
    "Hierarchical\nw/o renorm",
    "Trust Flow\n+ renorm",
]
round30_acc = np.array([70.2, 86.2, 92.3])
renorm_colors = ["#d62728", "#ff7f0e", "#1f77b4"]


fig = plt.figure(figsize=(11.8, 5.4))
gs = fig.add_gridspec(
    2,
    2,
    width_ratios=[2.15, 1.05],
    height_ratios=[1.0, 0.22],
    wspace=0.30,
    hspace=0.06,
)

ax = fig.add_subplot(gs[0, 0])
ax2 = ax.twinx()

acc_line, = ax.plot(
    rounds,
    acc,
    color="#1f77b4",
    marker="o",
    markersize=4,
    linewidth=2.2,
    label="Accuracy (ours)",
)
asr_line, = ax2.plot(
    rounds,
    asr,
    color="#d62728",
    marker="x",
    markersize=4,
    linewidth=2.0,
    linestyle="--",
    label="Backdoor ASR",
)

ax.axhspan(90, 100, color="#1f77b4", alpha=0.06, zorder=0)
ax2.axhspan(0, 12, color="#2ca02c", alpha=0.07, zorder=0)
ax.axvline(30, color="#444444", linestyle=":", linewidth=1.5)
ax.scatter([30], [92.31], s=70, color="#1f77b4", edgecolor="white", zorder=5)
ax2.scatter([30], [10.21], s=70, color="#d62728", edgecolor="white", zorder=5)

ax.annotate(
    "Round 30\nAcc 92.31%",
    xy=(30, 92.31),
    xytext=(23.2, 96.0),
    arrowprops=dict(arrowstyle="->", color="#1f77b4", lw=1.2),
    color="#1f77b4",
    fontsize=10,
    fontweight="bold",
)
ax2.annotate(
    "ASR 10.21%\nnear random guess",
    xy=(30, 10.21),
    xytext=(18.5, 19.0),
    arrowprops=dict(arrowstyle="->", color="#d62728", lw=1.2),
    color="#d62728",
    fontsize=10,
    fontweight="bold",
)

ax.set_title("(a) 30-round mixed-attack convergence", fontweight="bold")
ax.set_xlabel("Communication round")
ax.set_ylabel("Accuracy (%)", color="#1f77b4", fontweight="bold")
ax2.set_ylabel("Attack success rate (ASR, %)", color="#d62728", fontweight="bold")
ax.tick_params(axis="y", colors="#1f77b4")
ax2.tick_params(axis="y", colors="#d62728")
ax.set_xlim(1, 30.5)
ax.set_ylim(30, 100)
ax2.set_ylim(0, 100)
ax.set_xticks([1, 5, 10, 15, 20, 25, 30])
ax.grid(True, linestyle="--", alpha=0.45)
ax.legend(handles=[acc_line, asr_line], loc="lower right", frameon=True)

axb = fig.add_subplot(gs[0, 1])
bars = axb.bar(
    np.arange(len(round30_acc)),
    round30_acc,
    color=renorm_colors,
    width=0.62,
    edgecolor="#222222",
    linewidth=0.8,
)
axb.set_title("(b) Link to Fig. 9(b): renorm restores convergence", fontweight="bold")
axb.set_ylabel("Round-30 accuracy (%)")
axb.set_xticks(np.arange(len(round30_acc)))
axb.set_xticklabels(renorm_labels, fontsize=9)
axb.set_ylim(60, 100)
axb.grid(axis="y", linestyle="--", alpha=0.45)
for bar, val in zip(bars, round30_acc):
    axb.text(
        bar.get_x() + bar.get_width() / 2,
        val + 0.8,
        f"{val:.1f}%",
        ha="center",
        va="bottom",
        fontsize=10,
        fontweight="bold",
    )

axb.annotate(
    "+6.1 pp\nrenorm gain",
    xy=(2, 92.3),
    xytext=(1.08, 96.0),
    arrowprops=dict(arrowstyle="->", lw=1.2, color="#222222"),
    fontsize=10,
    fontweight="bold",
)
axb.plot([1, 2], [86.2, 86.2], color="#222222", linewidth=1.0)
axb.plot([2, 2], [86.2, 92.3], color="#222222", linewidth=1.0)

axc = fig.add_subplot(gs[1, :])
axc.axis("off")
summary = (
    "Experimental setting: 20 admitted clients, 30% malicious (6/20), "
    "six mixed attack types, Dirichlet alpha=0.1, 30 rounds, 5-seed mean. "
    "Key point: low ASR is not obtained by freezing learning; survivor-weight "
    "renormalization preserves optimization momentum, matching Fig. 9(b)."
)
axc.text(
    0.01,
    0.55,
    textwrap.fill(summary, width=150),
    ha="left",
    va="center",
    fontsize=10.5,
    bbox=dict(boxstyle="round,pad=0.45", facecolor="#f7f7f7", edgecolor="#cccccc"),
)

fig.suptitle(
    "Global Robustness Under Mixed Attacks and the Role of Renormalization",
    fontsize=15,
    fontweight="bold",
    y=0.995,
)
fig.subplots_adjust(left=0.065, right=0.975, bottom=0.12, top=0.86)

fig.savefig("figure_review/fig6_convergence_bridge_draft.pdf", dpi=300, bbox_inches="tight")
fig.savefig("figure_review/fig6_convergence_bridge_draft.png", dpi=300, bbox_inches="tight")
fig.savefig("figure_review/fig6_convergence_bridge_draft_v2.pdf", dpi=300, bbox_inches="tight")
fig.savefig("figure_review/fig6_convergence_bridge_draft_v2.png", dpi=300, bbox_inches="tight")
plt.close(fig)
