#!/usr/bin/env python3
"""Create a compact, reproducible summary for a saved matrix directory."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def pairs(text: str, key: str) -> list[float]:
    blocks = re.findall(rf"'{re.escape(key)}': \[(.*?)\]", text, re.S)
    if not blocks:
        return []
    return [float(value) for value in re.findall(r"\(\d+,\s*([0-9.eE+-]+)\)", blocks[-1])]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("matrix_dir", type=Path)
    args = parser.parse_args()
    rows = []
    for run_dir in sorted(p for p in args.matrix_dir.iterdir()
                          if p.is_dir() and ((p / 'manifest.json').exists() or (p / 'manifest.env').exists())):
        manifest = {}
        manifest_json = run_dir / "manifest.json"
        if manifest_json.exists():
            manifest = json.loads(manifest_json.read_text(encoding="utf-8"))
        manifest_path = run_dir / "manifest.env"
        if manifest_path.exists() and not manifest:
            for line in manifest_path.read_text(encoding="utf-8").splitlines():
                if "=" in line:
                    key, value = line.split("=", 1)
                    manifest[key] = value
        server_path = run_dir / 'server.log'
        server_text = server_path.read_text(encoding='utf-8', errors='replace') if server_path.exists() else ''
        completion_path = run_dir / 'completion.json'
        completion = json.loads(completion_path.read_text()) if completion_path.exists() else {}
        fit_results = [
            {"results": int(results), "failures": int(failures)}
            for results, failures in re.findall(
                r"aggregate_fit: received (\d+) results and (\d+) failures", server_text
            )
        ]
        item = {
            "run_id": run_dir.name,
            "status": completion.get('status', 'unknown'),
            "error": completion.get('error'),
            "method": manifest.get("method", manifest.get("METHOD", run_dir.name.split("_", 2)[1])),
            "scenario": manifest.get("scenario", manifest.get("SCENARIO", "unknown")),
            "seed": manifest.get("seed", manifest.get("SEED")),
            "clients": int(manifest.get("clients", manifest.get("CLIENTS", 0)) or 0),
            "rounds": int(manifest.get("rounds", manifest.get("ROUNDS", 0)) or 0),
            "clean_accuracy": pairs(server_text, "accuracy"),
            "backdoor_asr": pairs(server_text, "asr_backdoor"),
            "clean_label_asr": pairs(server_text, "asr_clean_label"),
            "fit_results": fit_results,
            "audit_available": False,
            "malicious_client_ids": manifest.get("malicious_client_ids", []),
        }
        metrics_path = run_dir / "round_metrics.jsonl"
        if metrics_path.exists():
            audit = [json.loads(line) for line in metrics_path.read_text().splitlines() if line.strip()]
            item["audit_available"] = True
            item["active_aggregation_clients"] = [row.get("active_aggregation_client_count") for row in audit]
            item["isolated_clients"] = [row.get("isolated_client_count") for row in audit]
            item["state_counts"] = [row.get("state_counts", {}) for row in audit]
            normal_ids = {str(i) for i in range(item['clients'])} - {str(i) for i in item['malicious_client_ids']}
            normal_clients = len(normal_ids)
            item["normal_client_count"] = normal_clients
            item["normal_client_exclusion_rate"] = [
                (sum(row['client_layer_stats'][cid]['included_layers'] == 0 for cid in normal_ids) / normal_clients
                 if normal_clients and normal_ids <= row.get('client_layer_stats', {}).keys() else None)
                for row in audit
            ]
        rows.append(item)

    first = rows[0] if rows else {}
    first_manifest = next(iter(sorted(args.matrix_dir.glob("*/manifest.json"))), None)
    protocol = json.loads(first_manifest.read_text(encoding="utf-8")) if first_manifest else {}
    protocol = {
        "dataset": protocol.get("dataset", "CIFAR-10 local"),
        "clients": protocol.get("clients", first.get("clients")),
        "rounds": protocol.get("rounds", first.get("rounds")),
        "local_epochs": protocol.get("local_epochs"),
        "shared_client_pool_size": protocol.get("shared_client_pool_size", 0),
        "server_proxy_size": protocol.get("server_proxy_size", 500),
        "known_trigger_probe": protocol.get("known_trigger_probe", False),
        "seed": protocol.get("seed"),
        "purpose": "development matrix; interpret only with the run manifests",
    }
    output = args.matrix_dir / "summary.json"
    output.write_text(json.dumps({"protocol": protocol, "runs": rows}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
