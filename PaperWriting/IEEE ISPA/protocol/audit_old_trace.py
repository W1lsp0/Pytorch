"""Join existing partial observations, leaving absent fields empty, not inferred.

This is archival diagnosis of Flwr/log/server.log, not controller verification.
"""
import csv
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
PAPER = HERE.parent
ROOT = PAPER.parents[1]
log_path = ROOT/"Flwr/log/server.log"
def read_csv(path):
    return list(csv.DictReader(path.open()))
states = {(int(x["round"]),int(x["client_id"])):x for x in read_csv(PAPER/"local_evidence/displayed_states.csv")}
layers = {(int(x["round"]),int(x["client_id"])):x for x in read_csv(PAPER/"local_evidence/client_layer_counts.csv")}
history, interceptions = {}, {}
round_id = None
for line_no, line in enumerate(log_path.read_text().splitlines(),1):
    match = re.search(r"\[ROUND (\d+)\]",line)
    if match:
        round_id = int(match[1])
    m = re.search(r"\[Client (\d+)\] S_contrib=.*?Hist=([0-9.]+)",line)
    if m:
        history[round_id,int(m[1])] = (m[2],line_no)
    m = re.search(r"\[Client (\d+)\] 黑名单拦截:.*\(([^)]+)\)",line)
    if m:
        interceptions[round_id,int(m[1])] = (m[2],line_no)
rows = []
for r in range(1,31):
    for k in range(20):
        current, previous = states.get((r,k),{}), states.get((r-1,k),{})
        counts = layers.get((r,k),{})
        ban = interceptions.get((r,k),(None,None))
        h = history.get((r,k),(None,None))
        rows.append(dict(round=r, client_id=k,
                         previous_displayed_state=previous.get("displayed_state"),
                         current_displayed_state=current.get("displayed_state"),
                         instant_risk=None, logged_risk_ema=current.get("risk_ema"),
                         logged_history=h[0], soft_streak=current.get("soft_streak"),
                         hard_streak=current.get("hard_streak"),
                         blacklist_interception_reason=ban[0],
                         selected_arrays=counts.get("included_arrays"),
                         actual_applied_norm=None,
                         state_source_line=current.get("server_log_line"),
                         history_source_line=h[1], interception_source_line=ban[1]))
out = HERE/"results/legacy_observed_events.csv"
with out.open("w",newline="") as f:
    writer = csv.DictWriter(f,fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
print(f"Wrote {len(rows)} archival rows; absent instantaneous risks and applied norms remain empty.")
