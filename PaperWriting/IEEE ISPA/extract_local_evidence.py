#!/usr/bin/env python3
"""Read existing logs only; do not import or execute the training application.

Outputs describe the single local trace, not the manuscript's ten-run study.
Code hashes identify the inspected snapshot, not the code used historically.
"""
import ast
import csv
import hashlib
import json
from pathlib import Path
import pickletools
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "local_evidence"
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def read(path):
    return ANSI.sub("", path.read_text())


def write_csv(name, rows):
    with (OUT / name).open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    OUT.mkdir(exist_ok=True)
    server_path = ROOT / "Flwr/log/server.log"
    server = read(server_path)
    history_text = "\n".join(re.sub(r"^INFO\s*:\s*", "", x)
                             for x in server.splitlines())
    start = history_text.index("{'accuracy':")
    end = history_text.index("]}", start) + 2
    history = ast.literal_eval(history_text[start:end])
    accuracy, asr = dict(history["accuracy"]), dict(history["asr"])
    if list(accuracy) != list(range(1, 31)) or list(asr) != list(accuracy):
        raise ValueError("Expected exactly one complete 30-round history")

    clients, client_metrics = [], []
    for cid in range(20):
        path = ROOT / f"Flwr/log/client_{cid}.log"
        log = read(path)
        count = re.search(r"样本数量: (\d+) 张 \(含公共池 (\d+) 张\)", log)
        attack = re.search(r"投毒模式: ([a-z_]+) \(比例: ([0-9.]+)%", log)
        if not attack and "正常模式: 无投毒攻击" not in log:
            raise ValueError(f"Unresolved attack mode for client {cid}")
        clients.append(dict(client_id=cid, train_records=int(count[1]),
                            shared_records=int(count[2]),
                            exclusive_records=int(count[1])-int(count[2]),
                            shared_fraction=int(count[2])/int(count[1]),
                            attack=attack[1] if attack else "none",
                            configured_poison_percent=float(attack[2]) if attack else 0,
                            source=str(path.relative_to(ROOT))))
        acc = re.findall(r"正常准确率 \(ACC\) : ([0-9.]+)%", log)
        bd = re.findall(r"Global BD ASR\s*: ([0-9.]+)%", log)
        cl = re.findall(r"Global CL ASR\s*: ([0-9.]+)%", log)
        if len(acc) != 30 or len(bd) != 30 or len(cl) != 30:
            raise ValueError(f"Incomplete global evaluation for client {cid}")
        for r, (a, b, c) in enumerate(zip(acc, bd, cl), 1):
            if abs(float(a)/100-accuracy[r]) > 1e-8 or abs(float(b)/100-asr[r]) > 1e-8:
                raise ValueError(f"Client/server history mismatch: {cid}, round {r}")
            client_metrics.append(dict(round=r, client_id=cid, accuracy_percent=a,
                                       bd_asr_percent=b, cl_asr_percent=c))

    rounds, layers, states, probes, bans, quarantines = [], [], [], [], {}, {}
    round_id = None
    for line_no, line in enumerate(server.splitlines(), 1):
        m = re.search(r"\[ROUND (\d+)\]", line)
        if m:
            round_id = int(m[1])
        if round_id is None:
            continue
        common = dict(round=round_id, server_log_line=line_no)
        m = re.search(r"NORMAL=(\d+) \| SUSPECT=(\d+) \| QUARANTINE=(\d+) \| BLACKLIST=(\d+)", line)
        if m:
            rounds.append(dict(**common, logged_normal=int(m[1]), logged_suspect=int(m[2]),
                               logged_quarantine=int(m[3]), logged_blacklist=int(m[4]),
                               accuracy=accuracy[round_id], bd_asr=asr[round_id]))
        m = re.search(r"Client\s+(\d+)\s+\| Inc:\s*(\d+)\s*\| Exc:\s*(\d+)\s*\| Scale:\s*([0-9.]+)x", line)
        if m:
            layers.append(dict(**common, client_id=int(m[1]), included_arrays=int(m[2]),
                               excluded_arrays=int(m[3]), logged_mean_clip_scale=float(m[4])))
        m = re.search(r"\[Client (\d+)\] State=(\w+) \| RiskEMA=([0-9.]+) \| PeerRiskEMA=([0-9.]+) \| SoftStreak=(\d+) \| HardStreak=(\d+) \| ProbeLoss=([0-9.]+) \| HeavyProbed=([YN])", line)
        if m:
            states.append(dict(**common, client_id=int(m[1]), displayed_state=m[2],
                               risk_ema=float(m[3]), peer_risk_ema=float(m[4]),
                               soft_streak=int(m[5]), hard_streak=int(m[6]),
                               logged_probe_loss=float(m[7]), heavy_probed=m[8]))
        m = re.search(r"动态离群门限: Median=([0-9.]+) \| MAD=([0-9.]+) \| Threshold=([0-9.]+) \| Source=(\S+) \| k=([0-9.]+)", line)
        if m:
            probes.append(dict(**common, median=float(m[1]), mad=float(m[2]),
                               threshold=float(m[3]), baseline_source=m[4], k=float(m[5])))
        m = re.search(r"\[Client (\d+)\] 黑名单拦截:.*\(([^)]+)\)", line)
        if m:
            bans.setdefault(int(m[1]), dict(**common, reason=m[2]))
        m = re.search(r"聚合隔离:.*\(Client IDs: ([0-9,]+)\)", line)
        if m:
            for cid in map(int, m[1].split(",")):
                quarantines.setdefault(cid, dict(**common))

    if len(rounds) != 30 or len(probes) != 30 or any(x["included_arrays"]+x["excluded_arrays"] != 122 for x in layers):
        raise ValueError("Unexpected audit coverage")
    malicious = {x["client_id"] for x in clients if x["attack"] != "none"}
    benign = set(range(20))-malicious
    if rounds[-1]["logged_blacklist"] != len(bans):
        raise ValueError("Final blacklist size/identity mismatch")
    elapsed = float(re.search(r"Run finished 30 round\(s\) in ([0-9.]+)s", server)[1])

    # Decode only integer label opcodes, without unpickling/executing dataset objects.
    dataset_path = ROOT / "Flwr/data/cifar-10-batches-py/test_batch"
    labels, in_labels = [], False
    for op, arg, _ in pickletools.genops(dataset_path.read_bytes()):
        if op.name in ("SHORT_BINSTRING", "BINSTRING", "BINUNICODE") and arg == "labels":
            in_labels = True
        elif in_labels and op.name in ("BININT", "BININT1", "BININT2"):
            labels.append(arg)
        if len(labels) == 10000:
            break
    if len(labels) != 10000 or any(labels.count(i) != 1000 for i in range(10)):
        raise ValueError("Unexpected CIFAR-10 test labels")
    counts, proxy = [0]*10, []
    for idx, label in enumerate(labels):
        if counts[label] < 50:
            proxy.append(idx)
            counts[label] += 1
    (OUT / "test_indices_from_snapshot.json").write_text(json.dumps(dict(
        provenance="Reconstructed from current server.py and stored CIFAR-10 labels; not a saved historical run index file",
        proxy_indices=proxy, noisy_probe_indices=proxy, evaluation_indices=list(range(10000)),
        proxy_evaluation_intersection=proxy, calibration_indices=None), indent=2)+"\n")

    for filename, rows in [("clients.csv", clients), ("client_global_metrics.csv", client_metrics),
                           ("rounds.csv", rounds), ("client_layer_counts.csv", layers),
                           ("displayed_states.csv", states), ("probe_thresholds.csv", probes)]:
        write_csv(filename, rows)
    code_paths = [ROOT / "Flwr" / p for p in (
        "run_simulation.sh", "Client/client.py", "Client/dataset.py", "Client/model.py",
        "Client/poison/attack_wrapper.py", "Client/tmaa/tee_sim.py", "Client/tmaa/sidecar.py",
        "Client/tmaa/monitor.py", "server/server.py", "server/strategy.py", "server/sensitivity.py",
        "server/trust_manager.py", "server/contribution.py")]
    sources = sorted((ROOT / "Flwr/log").glob("*.log")) + code_paths + [dataset_path]
    manifest = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    summary = dict(
        scope="One local diagnostic run; incompatible with ten-run, six-attacker main comparison",
        final_accuracy_percent=round(accuracy[30]*100, 2), final_bd_asr_percent=round(asr[30]*100, 2),
        final_cl_asr_percent=float(client_metrics[29]["cl_asr_percent"]),
        run_count=1, rounds=30, benign_clients=len(benign), malicious_clients=len(malicious),
        final_benign_bans=len(benign & bans.keys()), final_malicious_bans=len(malicious & bans.keys()),
        first_blacklist_intercept=bans, first_aggregation_quarantine=quarantines,
        total_training_records=sum(x["train_records"] for x in clients),
        logged_flower_run_seconds=elapsed, seconds_per_round_amortized=elapsed/30,
        gate_audit_rows=len(layers), top8_state_observations=len(states),
        positive_gate_rows=sum(x["included_arrays"]>0 for x in layers),
        benign_positive_gate_rows=sum(x["included_arrays"]>0 and x["client_id"] in benign for x in layers),
        warnings=["Gate counts are not numeric applied weights or proof of nonzero model contribution",
                  "State display covers only the top eight; category totals can overlap on a blacklisting round",
                  "ASR includes target-class samples; no semantic targeted ASR is logged",
                  "Hardware telemetry and TEE are simulated in this local run",
                  "Elapsed time is the Flower run, not isolated audit, attestation or aggregation time",
                  "Current code hashes do not establish the historical execution version",
                  "No ten-run means/SDs or ablation results are reconstructed"],
        source_sha256=manifest)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False)+"\n")
    print(json.dumps({k:v for k,v in summary.items() if k not in ("source_sha256", "warnings")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
