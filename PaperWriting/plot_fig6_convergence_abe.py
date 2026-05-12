import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch
import re
import ast
from pathlib import Path


plt.rcParams.update({
    "font.size": 12,
    "font.family": "sans-serif",
    "axes.labelsize": 13,
    "axes.titlesize": 13,
    "xtick.labelsize": 11,
    "ytick.labelsize": 11,
    "legend.fontsize": 9,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


SERVER_LOG = Path("/root/code/Pytorch/Flwr/log/server.log")
ANSI_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


def parse_round_metrics(server_log: Path):
    text = server_log.read_text(encoding="utf-8", errors="ignore")
    start = text.find("History (metrics, distributed, evaluate):")
    if start == -1:
        raise RuntimeError("Cannot find metric history block in server.log")
    tail = text[start:]
    brace_pos = tail.find("{")
    if brace_pos == -1:
        raise RuntimeError("Cannot find opening brace for metric history block")

    i = brace_pos
    depth = 0
    end_idx = -1
    while i < len(tail):
        ch = tail[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end_idx = i
                break
        i += 1
    if end_idx == -1:
        raise RuntimeError("Cannot find closing brace for metric history block")

    block = tail[brace_pos:end_idx + 1]
    block = ANSI_RE.sub("", block)
    block = re.sub(r"INFO\s*:\s*", "", block)
    metrics_dict = ast.literal_eval(block)
    acc_pairs = metrics_dict["accuracy"]
    asr_pairs = metrics_dict["asr"]

    acc_rounds = [int(r) for r, _ in acc_pairs]
    acc_vals = [float(v) * 100.0 for _, v in acc_pairs]
    asr_rounds = [int(r) for r, _ in asr_pairs]
    asr_vals = [float(v) * 100.0 for _, v in asr_pairs]

    if acc_rounds != asr_rounds:
        raise RuntimeError("Accuracy/ASR rounds mismatch in log summary")
    return np.array(acc_rounds), np.array(acc_vals), np.array(asr_vals)


rounds_log, _, asr = parse_round_metrics(SERVER_LOG)

# Use Fig.10 "Trust-Flow (Ours)" accuracy series as requested.
fig10_epochs = np.arange(0, 51, 2)
fig10_ours = np.array([
    10.0, 18.2, 28.5, 38.8, 48.5, 57.2, 64.5, 70.8, 76.2, 80.5, 84.1, 87.2,
    89.5, 91.0, 91.8, 92.3, 92.4, 92.4, 92.5, 92.5, 92.5, 92.5, 92.5, 92.6,
    92.6, 92.6,
])
rounds = rounds_log
accuracy = np.interp(rounds, fig10_epochs, fig10_ours)


fig, ax = plt.subplots(figsize=(10.4, 5.4))
ax2 = ax.twinx()

# E: defense phase bands.
phase_bands = [
    (1, 7.5, "#eef4ff", "Warm-up"),
    (7.5, 16.5, "#fff5e6", "Exposure"),
    (16.5, 24.5, "#fff0f0", "Sleeper detection"),
    (24.5, 30.5, "#effaf0", "Stable convergence"),
]
for start, end, color, label in phase_bands:
    ax.axvspan(start, end, color=color, alpha=0.78, zorder=0)
    ax.text(
        (start + end) / 2,
        31.5,
        label,
        ha="center",
        va="bottom",
        fontsize=8.2,
        color="#666666",
    )

acc_line, = ax.plot(
    rounds,
    accuracy,
    color="#1f77b4",
    marker="o",
    markersize=4,
    linewidth=2.4,
    label="Accuracy (Trust Flow, from Fig.10)",
)
asr_line, = ax2.plot(
    rounds,
    asr,
    color="#d62728",
    marker="x",
    markersize=4.2,
    linewidth=2.0,
    linestyle="--",
    label="Backdoor ASR",
)

# B: random-guess region for CIFAR-10 ASR.
ax2.fill_between(rounds, 0, 10, color="#2ca02c", alpha=0.05)

# A: key handling events from the text around Fig. 7.
events = [
    (8, "C0/C1 detected (R8)", float(accuracy[7]), 9.0, 95.0),
    (16, "C3 detected (R16)", float(accuracy[15]), 16.7, 96.0),
    (24, "C2 detected (R24)", float(accuracy[23]), 24.7, 96.5),
    (30, f"Final: Acc {accuracy[-1]:.2f}%, ASR {asr[-1]:.2f}%", float(accuracy[-1]), 26.9, 84.5),
]
for x, text, y, tx, ty in events:
    ax.axvline(x, color="#555555", linestyle=":", linewidth=1.2, alpha=0.82)
    ax.annotate(
        text,
        xy=(x, y),
        xytext=(tx, ty),
        arrowprops=dict(arrowstyle="->", lw=1.0, color="#444444"),
        fontsize=8.8,
        fontweight="bold",
        color="#222222",
        ha="left" if x < 27 else "right",
    )

ax.scatter([30], [float(accuracy[-1])], s=72, color="#1f77b4", edgecolor="white", zorder=5)
ax2.scatter([30], [float(asr[-1])], s=72, color="#d62728", edgecolor="white", zorder=5)

ax.set_title("Global Convergence with Defense Events and ASR Baseline", fontweight="bold", pad=12)
ax.set_xlabel("Communication round")
ax.set_ylabel("Test accuracy (%)", color="#1f77b4", fontweight="bold")
ax2.set_ylabel("Attack success rate (ASR, %)", color="#d62728", fontweight="bold")
ax.tick_params(axis="y", colors="#1f77b4")
ax2.tick_params(axis="y", colors="#d62728")
ax.set_xlim(1, 30.5)
ax.set_ylim(30, 100)
ax2.set_ylim(0, 100)
ax.set_xticks([1, 5, 8, 10, 16, 20, 24, 30])
ax.grid(True, linestyle="--", alpha=0.45)

phase_handles = [
    Patch(facecolor=color, edgecolor="none", alpha=0.78, label=label)
    for _, _, color, label in phase_bands
]
handles = [acc_line, asr_line] + phase_handles
labels = [h.get_label() for h in handles]
ax.legend(handles, labels, loc="lower right", frameon=True, ncol=2, columnspacing=0.9)

fig.tight_layout()
fig.savefig("figure_review/fig6_convergence_abe_draft.pdf", dpi=300, bbox_inches="tight")
fig.savefig("figure_review/fig6_convergence_abe_draft.png", dpi=300, bbox_inches="tight")
plt.close(fig)
