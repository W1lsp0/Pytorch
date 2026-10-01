from pathlib import Path
import re
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

LOG = Path("/root/code/Pytorch/Flwr/log/server.log")
OUT = Path("/root/code/Pytorch/PaperWriting/IEEE ISPA/figures_actual")
OUT.mkdir(parents=True, exist_ok=True)

text = LOG.read_text(errors="ignore")
round_rows = [(int(a), int(b), int(c)) for a, b, c in re.findall(
    r"第 (\d+) 轮聚合完成 \| 存活节点: (\d+) \| 拦截: (\d+)", text
)]
acc_block = re.search(r"'accuracy': \[(.*?)\]", text, re.S).group(1)
acc = [float(v) for v in re.findall(r"\(\d+, ([0-9.]+)\)", acc_block)]

client_log = Path("/root/code/Pytorch/Flwr/log/client_0.log").read_text(errors="ignore")
bd = [float(v) / 100 for v in re.findall(r"Global BD ASR\s+: ([0-9.]+)%", client_log)][-30:]
cl = [float(v) / 100 for v in re.findall(r"Global CL ASR\s+: ([0-9.]+)%", client_log)][-30:]
rounds = list(range(1, len(acc) + 1))
remaining = [row[1] for row in round_rows]
blacklist = [row[2] for row in round_rows]

plt.rcParams.update({"font.size": 8, "font.family": "sans-serif"})
fig, (ax1, ax2) = plt.subplots(
    2, 1, figsize=(6.7, 4.4), sharex=True,
    gridspec_kw={"height_ratios": [1.35, 1]}
)

ax1.plot(rounds, [v * 100 for v in acc], color="#1f77b4", lw=1.8,
         marker="o", ms=2.5, label="Clean accuracy")
ax1.plot(rounds, [v * 100 for v in bd], color="#d62728", lw=1.4,
         marker="s", ms=2.2, label="BD triggered-test accuracy")
ax1.plot(rounds, [v * 100 for v in cl], color="#ff7f0e", lw=1.2,
         marker="^", ms=2.2, label="CL triggered-test accuracy")
ax1.set_ylabel("Percentage (%)")
ax1.set_ylim(0, 100)
ax1.grid(alpha=.25, lw=.5)
ax1.legend(loc="center right", frameon=True, fontsize=7)
ax1.set_title("Single completed run: model quality and triggered-test accuracy")

ax2.step(rounds, remaining, where="mid", color="#2ca02c", lw=1.8,
         label="Clients after blacklist screen")
ax2.step(rounds, blacklist, where="mid", color="#9467bd", lw=1.8,
         label="Blacklist rejections")
ax2.set_xlabel("Federated round")
ax2.set_ylabel("Clients")
ax2.set_ylim(bottom=0, top=21)
ax2.set_yticks([0, 4, 8, 12, 16, 20])
ax2.grid(alpha=.25, lw=.5)
ax2.legend(loc="center right", frameon=True, fontsize=7)
for x in [8, 16, 24]:
    ax2.axvline(x, color="0.4", lw=.7, ls=":")

fig.tight_layout(pad=.8)
fig.savefig(OUT / "actual_run.pdf", bbox_inches="tight")
fig.savefig(OUT / "actual_run.png", dpi=220, bbox_inches="tight")

