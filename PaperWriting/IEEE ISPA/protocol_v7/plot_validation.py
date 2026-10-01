"""Plot executed synthetic controller traces; never edit historical figures.

Contract: one 3.5-inch column, three panels: risk, state, applied update norm.
Input: results CSVs from validate.py; deterministic fixture, no error bars/SD.
"""
import csv
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
states = [r for r in csv.DictReader((RESULTS/"state_events.csv").open())
          if r["case"] == "collective_recovery" and r["client_id"] == "0"]
layers = list(csv.DictReader((RESULTS/"layer_events.csv").open()))
plt.rcParams.update({"font.family":"DejaVu Serif", "font.size":8, "pdf.fonttype":42,
                     "svg.fonttype":"none", "axes.spines.top":False,
                     "axes.spines.right":False, "axes.linewidth":.7,
                     "legend.frameon":False})
fig, axes = plt.subplots(3, 1, figsize=(3.5, 4.4), sharex=True, layout="constrained")
x = [0]+[int(r["round"]) for r in states]
axes[0].plot(x, [.95]+[float(r["risk_ema"]) for r in states], "o-", color="#205f85", markersize=3, label="Risk EMA")
axes[0].axhline(.64, color="0.3", linestyle="--", linewidth=.9, label="Review threshold")
axes[0].set(ylabel="Risk", ylim=(0,1.03), title="(a) Risk during recovery")
axes[0].legend(fontsize=7, loc="upper right")
mapping = {"QUARANTINE":0, "SUSPECT":1, "NORMAL":2}
axes[1].step(x, [0]+[mapping[r["end_state"]] for r in states], where="post", color="#205f85", linewidth=1.3)
axes[1].plot(x, [0]+[mapping[r["end_state"]] for r in states], "s", color="#205f85", markersize=3)
axes[1].set(yticks=[0,1,2], yticklabels=["Quarantine","Suspect","Normal"], ylim=(-.25,2.25), title="(b) State after each audit")
axes[2].plot(x, [0.]+[float(r["applied_norm"]) for r in layers], "^-", color="#205f85", markersize=3)
axes[2].set(ylabel="Applied update norm (a.u.)", xlabel="Recovery audit round", ylim=(0,1.08), title="(c) Applied toy update")
for ax in axes:
    ax.set_xlim(0,10)
    ax.set_xticks(range(0,11,2))
    ax.grid(axis="y", alpha=.2, linewidth=.5)
for ext in ("pdf", "svg", "png"):
    fig.savefig(RESULTS/f"collective_recovery.{ext}", dpi=300)
plt.close(fig)
