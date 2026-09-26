#!/usr/bin/env python3
"""Summarize machine-readable audit coverage for one saved run directory."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    metrics_path = args.run_dir / "round_metrics.jsonl"
    if not metrics_path.exists():
        # FedAvg and other aggregation baselines may not expose TTFL's
        # per-client state audit.  Keep the run machine-readable and make the
        # missing audit explicit instead of aborting the whole matrix.
        summary = {
            "run_dir": str(args.run_dir),
            "rounds": None,
            "audit_available": False,
            "audit_note": "round_metrics.jsonl not emitted by this method",
            "probe_policy": {},
            "probe_coverage": {"min": None, "max": None, "per_round": []},
            "aggregation": {"min_active_clients": None, "max_isolated_clients": None},
            "state_count_changes": [],
        }
        output = args.run_dir / "analysis_summary.json"
        output.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return

    rows = [json.loads(line) for line in metrics_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows.sort(key=lambda row: int(row["round"]))
    transitions = []
    previous = {}
    for row in rows:
        states = row.get("client_layer_stats", {})
        counts = row.get("state_counts", {})
        for state, count in counts.items():
            previous_key = f"count:{state}"
            if previous.get(previous_key) != count:
                transitions.append({"round": row["round"], "state": state, "count": count})
            previous[previous_key] = count

    summary = {
        "run_dir": str(args.run_dir),
        "audit_available": True,
        "rounds": len(rows),
        "probe_policy": {
            "known_trigger_probe": rows[0].get("known_trigger_probe"),
            "heavy_probe_rotate_mod": rows[0].get("heavy_probe_rotate_mod"),
        },
        "probe_coverage": {
            "min": min(int(row.get("heavy_probed_count", 0)) for row in rows),
            "max": max(int(row.get("heavy_probed_count", 0)) for row in rows),
            "per_round": [
                {"round": row["round"], "heavy_probed_count": row.get("heavy_probed_count", 0)}
                for row in rows
            ],
        },
        "aggregation": {
            "min_active_clients": min(int(row.get("active_aggregation_client_count", 0)) for row in rows),
            "max_isolated_clients": max(int(row.get("isolated_client_count", 0)) for row in rows),
        },
        "state_count_changes": transitions,
    }
    output = args.run_dir / "analysis_summary.json"
    output.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
