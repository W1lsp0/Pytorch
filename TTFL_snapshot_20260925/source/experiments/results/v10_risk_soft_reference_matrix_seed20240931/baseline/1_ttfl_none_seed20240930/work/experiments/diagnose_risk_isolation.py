#!/usr/bin/env python3
"""Summarize machine-readable risk isolation causes from completed runs."""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def load_run(run_dir: Path):
    manifest = json.loads((run_dir / "manifest.json").read_text())
    rows = []
    with (run_dir / "round_metrics.jsonl").open() as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    return manifest, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("result_root", type=Path)
    ap.add_argument("--allow-incomplete", action="store_true")
    args = ap.parse_args()
    root = args.result_root.resolve()
    runs = []
    for run_dir in sorted(p for p in root.iterdir() if p.is_dir() and (p / "manifest.json").exists()):
        metrics = run_dir / "round_metrics.jsonl"
        if not metrics.exists():
            continue
        manifest, rows = load_run(run_dir)
        expected = int(manifest["rounds"])
        if not args.allow_incomplete and len(rows) != expected:
            raise SystemExit(f"incomplete {run_dir.name}: {len(rows)}/{expected} rounds")
        runs.append((run_dir, manifest, rows))
    if not runs:
        raise SystemExit("no run metrics found")

    summaries = []
    for run_dir, manifest, rows in runs:
        scenario = manifest["scenario"]
        malicious = {"1"} if scenario != "none" else set()
        reasons = Counter()
        identity_reasons = Counter()
        isolated_rows = []
        channel_sums = defaultdict(float)
        channel_n = 0
        for row in rows:
            for cid, audit in row.get("risk_decision_audit", {}).items():
                reason = audit.get("isolation_reason", "unknown")
                isolated = bool(audit.get("risk_isolated")) or bool(audit.get("blacklisted"))
                if isolated:
                    reasons[reason] += 1
                    identity = "malicious" if cid in malicious else "normal"
                    identity_reasons[(identity, reason)] += 1
                    isolated_rows.append((int(row.get("round", 0)), cid, identity, reason))
                    for key in ("risk_new", "probe_risk", "grad_risk", "trigger_risk", "pixel_risk", "peer_effective", "soft_hit_count"):
                        channel_sums[key] += float(audit.get(key, 0.0))
                    channel_n += 1
        avg_channels = {k: (v / channel_n if channel_n else 0.0) for k, v in channel_sums.items()}
        summaries.append({
            "run_id": run_dir.name,
            "scenario": scenario,
            "seed": manifest["seed"],
            "rounds_read": len(rows),
            "isolation_reason_counts": dict(reasons),
            "identity_reason_counts": {f"{a}:{b}": n for (a, b), n in sorted(identity_reasons.items())},
            "isolated_records": len(isolated_rows),
            "average_channels_on_isolated_records": avg_channels,
            "first_isolation": isolated_rows[0] if isolated_rows else None,
        })

    output = {"result_root": str(root), "runs": summaries}
    (root / "risk_isolation_diagnosis.json").write_text(json.dumps(output, indent=2, ensure_ascii=False))
    lines = ["# Risk isolation diagnosis", "", f"Result root: `{root}`", ""]
    for item in summaries:
        lines += [
            f"## {item['run_id']}",
            f"- scenario: `{item['scenario']}`; rounds read: {item['rounds_read']}",
            f"- isolation reasons: `{json.dumps(item['isolation_reason_counts'], ensure_ascii=False)}`",
            f"- identity × reason: `{json.dumps(item['identity_reason_counts'], ensure_ascii=False)}`",
            f"- first isolation: `{item['first_isolation']}`",
            f"- average channels on isolated records: `{json.dumps(item['average_channels_on_isolated_records'], ensure_ascii=False)}`",
            "",
        ]
    (root / "risk_isolation_diagnosis.md").write_text("\n".join(lines), encoding="utf-8")
    print(root / "risk_isolation_diagnosis.md")


if __name__ == "__main__":
    main()
