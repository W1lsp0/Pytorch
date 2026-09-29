#!/usr/bin/env python3
"""Compare baseline and cross-channel-guard matrices using risk audits."""
import argparse
import json
from collections import Counter
from pathlib import Path


def read_matrix(root: Path):
    summary = json.loads((root / "summary.json").read_text())
    runs = {}
    for item in summary["runs"]:
        run_dir = root / item["run_id"]
        manifest = json.loads((run_dir / "manifest.json").read_text())
        rows = [json.loads(line) for line in (run_dir / "round_metrics.jsonl").read_text().splitlines() if line.strip()]
        runs[manifest["scenario"]] = (manifest, item, rows)
    return runs


def measure(manifest, summary, rows):
    malicious = {"1"} if manifest["scenario"] != "none" else set()
    normal = {str(i) for i in range(manifest["clients"])} - malicious
    normal_excluded = []
    malicious_isolated = []
    reason_counts = Counter()
    first_attack = None
    for row in rows:
        audits = row.get("risk_decision_audit", {})
        excluded_normal = 0
        for cid in normal:
            a = audits.get(cid, {})
            if a.get("risk_isolated") or a.get("blacklisted"):
                excluded_normal += 1
                reason_counts[f"normal:{a.get('isolation_reason', 'unknown')}"] += 1
        normal_excluded.append(excluded_normal)
        attacked = any(
            (audits.get(cid, {}).get("risk_isolated") or audits.get(cid, {}).get("blacklisted"))
            for cid in malicious
        )
        if attacked:
            malicious_isolated.append(int(row["round"]))
            if first_attack is None:
                first_attack = int(row["round"])
    return {
        "scenario": manifest["scenario"],
        "seed": manifest["seed"],
        "guard": bool(manifest.get("risk_cross_channel_guard", False)),
        "rounds": len(rows),
        "final_accuracy": float(summary["clean_accuracy"][-1]),
        "final_asr": float(summary["backdoor_asr"][-1]),
        "attack_window_mean_asr": float(sum(summary["backdoor_asr"][10:23]) / len(summary["backdoor_asr"][10:23])) if manifest["scenario"] != "none" else None,
        "normal_excluded_total": int(sum(normal_excluded)),
        "normal_client_rounds": int(len(rows) * len(normal)),
        "normal_exclusion_rate": float(sum(normal_excluded) / (len(rows) * len(normal))),
        "max_normal_excluded_in_round": int(max(normal_excluded, default=0)),
        "first_malicious_isolation_round": first_attack,
        "malicious_isolated_rounds": malicious_isolated,
        "reason_counts": dict(reason_counts),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("baseline", type=Path)
    ap.add_argument("candidate", type=Path)
    args = ap.parse_args()
    base = read_matrix(args.baseline.resolve())
    cand = read_matrix(args.candidate.resolve())
    if set(base) != set(cand):
        raise SystemExit(f"scenario mismatch: {set(base)} vs {set(cand)}")
    report = {"baseline_root": str(args.baseline.resolve()), "candidate_root": str(args.candidate.resolve()), "scenarios": {}}
    for scenario in sorted(base):
        b = measure(*base[scenario])
        c = measure(*cand[scenario])
        report["scenarios"][scenario] = {
            "baseline": b,
            "candidate": c,
            "delta": {
                "final_accuracy": c["final_accuracy"] - b["final_accuracy"],
                "final_asr": c["final_asr"] - b["final_asr"],
                "attack_window_mean_asr": (c["attack_window_mean_asr"] - b["attack_window_mean_asr"])
                if c["attack_window_mean_asr"] is not None else None,
                "normal_excluded_total": c["normal_excluded_total"] - b["normal_excluded_total"],
                "normal_exclusion_rate": c["normal_exclusion_rate"] - b["normal_exclusion_rate"],
            },
        }
    out = args.candidate.resolve()
    (out / "cross_channel_guard_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    lines = ["# Cross-channel guard paired report", "", f"Baseline: `{args.baseline.resolve()}`", f"Candidate: `{args.candidate.resolve()}`", ""]
    for scenario, item in report["scenarios"].items():
        b, c, d = item["baseline"], item["candidate"], item["delta"]
        lines += [
            f"## {scenario}",
            f"- final accuracy: {b['final_accuracy']:.4f} → {c['final_accuracy']:.4f} (Δ {d['final_accuracy']:+.4f})",
            f"- final ASR: {b['final_asr']:.4f} → {c['final_asr']:.4f} (Δ {d['final_asr']:+.4f})",
            f"- attack-window mean ASR: {b['attack_window_mean_asr']} → {c['attack_window_mean_asr']} (Δ {d['attack_window_mean_asr']})",
            f"- normal exclusions: {b['normal_excluded_total']}/{b['normal_client_rounds']} → {c['normal_excluded_total']}/{c['normal_client_rounds']} (Δ {d['normal_excluded_total']:+d}; rate Δ {d['normal_exclusion_rate']:+.4%})",
            f"- max normal excluded in one round: {b['max_normal_excluded_in_round']} → {c['max_normal_excluded_in_round']}",
            f"- first malicious isolation: {b['first_malicious_isolation_round']} → {c['first_malicious_isolation_round']}",
            f"- reasons baseline: `{json.dumps(b['reason_counts'], ensure_ascii=False)}`",
            f"- reasons candidate: `{json.dumps(c['reason_counts'], ensure_ascii=False)}`",
            "",
        ]
    (out / "cross_channel_guard_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(out / "cross_channel_guard_report.md")


if __name__ == "__main__":
    main()
