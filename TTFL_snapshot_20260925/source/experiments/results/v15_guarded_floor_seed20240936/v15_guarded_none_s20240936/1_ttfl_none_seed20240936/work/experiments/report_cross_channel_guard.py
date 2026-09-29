#!/usr/bin/env python3
"""Compare baseline and cross-channel-guard matrices using risk audits."""
import argparse
import json
from collections import Counter
import math
import re
from compare_probe_conditions import artifacts, FIELDS
from report_long_window import read_run
from pathlib import Path


def read_matrix(root: Path):
    summary = json.loads((root / "summary.json").read_text())
    runs = {}
    for item in summary["runs"]:
        run_dir = root / item["run_id"]
        manifest = json.loads((run_dir / "manifest.json").read_text())
        rows = [json.loads(line) for line in (run_dir / "round_metrics.jsonl").read_text().splitlines() if line.strip()]
        scenario = manifest["scenario"]
        if scenario in runs:
            raise ValueError(f"duplicate scenario: {scenario}")
        if json.loads((run_dir / "completion.json").read_text())["status"] != "success":
            raise ValueError(f"unsuccessful run: {run_dir}")
        expected_ids = {str(i) for i in range(manifest["clients"])}
        if [r["round"] for r in rows] != list(range(1, manifest["rounds"] + 1)):
            raise ValueError(f"incomplete rounds: {run_dir}")
        for row in rows:
            if set(row.get("risk_decision_audit", {})) != expected_ids or set(row["client_layer_stats"]) != expected_ids:
                raise ValueError(f"missing client audit: {run_dir}, round {row['round']}")
            for a in row["risk_decision_audit"].values():
                if any(not math.isfinite(v) for v in a.values() if isinstance(v, float)):
                    raise ValueError("non-finite risk audit")
                if bool(a.get("cross_channel_guard", False)) != bool(manifest.get("risk_cross_channel_guard", False)):
                    raise ValueError("guard audit/manifest mismatch")
        verified = read_run(run_dir)
        if item["clean_accuracy"] != verified["clean_accuracy"] or item["backdoor_asr"] != verified["backdoor_asr"]:
            raise ValueError("summary differs from original evaluation log")
        for cid in manifest["malicious_client_ids"]:
            actual = [(int(n), flag == 'True') for n, flag in re.findall(r'Round (\d+) [^\n]*attack_active=(True|False)', (run_dir / f'client_{cid}.log').read_text())]
            expected = [(n, n >= manifest['attack_start_round'] and (not manifest['attack_stop_round'] or n < manifest['attack_stop_round'])) for n in range(1, manifest['rounds'] + 1)]
            if actual != expected:
                raise ValueError("attack schedule mismatch")
        runs[scenario] = (manifest, item, rows)
    return runs


def measure(manifest, summary, rows):
    malicious = {str(i) for i in manifest["malicious_client_ids"]}
    normal = {str(i) for i in range(manifest["clients"])} - malicious
    normal_excluded = []
    normal_isolated = []
    fully_excluded_attack_rounds = []
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
        normal_isolated.append(excluded_normal)
        normal_excluded.append(sum(row['client_layer_stats'][cid]['included_layers'] == 0 for cid in normal))
        if any(row['client_layer_stats'][cid]['included_layers'] == 0 for cid in malicious):
            fully_excluded_attack_rounds.append(int(row['round']))
        attacked = any(
            (audits.get(cid, {}).get("risk_isolated") or audits.get(cid, {}).get("blacklisted"))
            for cid in malicious
        )
        if attacked:
            malicious_isolated.append(int(row["round"]))
            if first_attack is None:
                first_attack = int(row["round"])
    start = manifest['attack_start_round']
    stop = manifest['attack_stop_round'] - 1 if manifest['attack_stop_round'] else manifest['rounds']
    window = summary['backdoor_asr'][start - 1:stop] if malicious else []
    return {
        "attack_window_rounds": [start, stop] if malicious else None,
        "normal_explicit_isolation_total": sum(normal_isolated),
        "malicious_fully_excluded_rounds": fully_excluded_attack_rounds,
        "attack_window_peak_asr": max(window) if window else None,
        "scenario": manifest["scenario"],
        "seed": manifest["seed"],
        "guard": bool(manifest.get("risk_cross_channel_guard", False)),
        "rounds": len(rows),
        "final_accuracy": float(summary["clean_accuracy"][-1]),
        "final_asr": float(summary["backdoor_asr"][-1]),
        "attack_window_mean_asr": sum(window) / len(window) if window else None,
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
    if set(base) != {"none", "backdoor", "delayed_backdoor"} or set(base) != set(cand):
        raise SystemExit(f"scenario mismatch: {set(base)} vs {set(cand)}")
    report = {"baseline_root": str(args.baseline.resolve()), "candidate_root": str(args.candidate.resolve()), "scenarios": {}}
    for scenario in sorted(base):
        bm, cm = base[scenario][0], cand[scenario][0]
        for field in (*FIELDS, 'known_trigger_probe', 'heavy_probe_rotate_mod', 'trigger_score_mode', 'risk_raw_attenuation_power'):
            if bm.get(field) != cm.get(field):
                raise ValueError(f"paired protocol mismatch: {field}")
        if bm.get('risk_cross_channel_guard', False) or not cm.get('risk_cross_channel_guard', False):
            raise ValueError("expected baseline guard=0 and candidate guard=1")
        br, cr = args.baseline / base[scenario][1]['run_id'], args.candidate / cand[scenario][1]['run_id']
        ba, ca = artifacts(br, bm), artifacts(cr, cm)
        if any(ba[k] != ca[k] for k in ('initial_sha256', 'partition_sha256')):
            raise ValueError("paired initialization/partition mismatch")
        def sources(run):
            work = run / 'work'
            return {str(p.relative_to(work)): p.read_bytes() for p in [*work.glob('*.py'), *(work/'Client').rglob('*.py'), *(work/'server').rglob('*.py')]}
        bs, cs = sources(br), sources(cr)
        changed = sorted(k for k in set(bs) | set(cs) if bs.get(k) != cs.get(k))
        if set(changed) - {'server/trust_manager.py'}:
            raise ValueError(f"unplanned training-source changes: {changed}")
        if bm['seed'] != 20240928 and changed:
            raise ValueError("independent comparison must use identical training sources")
        b = measure(*base[scenario])
        c = measure(*cand[scenario])
        report["scenarios"][scenario] = {
            "validation": {"baseline": ba, "candidate": ca, "changed_training_files": changed},
            "baseline": b,
            "candidate": c,
            "delta": {
                "final_accuracy": c["final_accuracy"] - b["final_accuracy"],
                "final_asr": c["final_asr"] - b["final_asr"],
                "attack_window_mean_asr": (c["attack_window_mean_asr"] - b["attack_window_mean_asr"])
                if c["attack_window_mean_asr"] is not None else None,
                "normal_explicit_isolation_total": c["normal_explicit_isolation_total"] - b["normal_explicit_isolation_total"],
                "normal_excluded_total": c["normal_excluded_total"] - b["normal_excluded_total"],
                "normal_exclusion_rate": c["normal_exclusion_rate"] - b["normal_exclusion_rate"],
            },
        }
    report['complete'] = True
    report['scope'] = 'Two intervention sites: guarded soft gate with soft_strong bypass retained, and guarded C2 quarantine hit. Temporal/spectral/sign are extra evidence channels, not proven statistically independent. Default guard remains off; known-trigger clean_delta study, one seed per report.'
    out = args.candidate.resolve()
    (out / "cross_channel_guard_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    lines = ["# Cross-channel guard paired report", "", f"Baseline: `{args.baseline.resolve()}`", f"Candidate: `{args.candidate.resolve()}`", ""]
    lines += [report["scope"], "", "Normal exclusions use included_layers=0; explicit isolation is reported separately. Attack-window endpoints come from each manifest; stop is exclusive.", ""]
    for scenario, item in report["scenarios"].items():
        b, c, d = item["baseline"], item["candidate"], item["delta"]
        lines += [
            f"## {scenario}",
            f"- final accuracy: {b['final_accuracy']:.4f} → {c['final_accuracy']:.4f} (Δ {d['final_accuracy']:+.4f})",
            f"- final ASR: {b['final_asr']:.4f} → {c['final_asr']:.4f} (Δ {d['final_asr']:+.4f})",
            f"- attack-window rounds: {b['attack_window_rounds']}; peak ASR: {b['attack_window_peak_asr']} → {c['attack_window_peak_asr']}",
            f"- explicit normal isolations: {b['normal_explicit_isolation_total']} → {c['normal_explicit_isolation_total']}",
            f"- malicious isolated rounds: {b['malicious_isolated_rounds']} → {c['malicious_isolated_rounds']}",
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
