#!/usr/bin/env python3
"""Compare two TTFL calibration summaries and emit Markdown evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def first_suspect(summary: dict) -> str:
    for key, value in summary.get("state_audit", {}).items():
        if "client_1" in key and value == "SUSPECT":
            return key.replace("client_1", "C1")
    return "未进入 SUSPECT"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("baseline", type=Path)
    parser.add_argument("probe", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    base = load(args.baseline)
    probe = load(args.probe)
    b_asr = base["round_metrics"]["asr_backdoor"]
    p_asr = probe["round_metrics"]["asr_backdoor"]
    lines = [
        "| 配置 | 已知触发器探针 | 探针轮换 | 攻击启动轮 ASR | 最终 ASR | C1 首次 SUSPECT | 最终采纳层数 |",
        "|---|---:|---:|---:|---:|---|---:|",
        f"| 默认轮换 | {base['protocol']['known_trigger_probe']} | {base['protocol'].get('heavy_probe_rotate_mod', 5)} | {b_asr[2]:.2%} | {b_asr[-1]:.2%} | {first_suspect(base)} | {base['state_audit']['round_6_client_1_included_layers']} |",
        f"| 每轮已知触发器 | {probe['protocol']['known_trigger_probe']} | {probe['protocol']['heavy_probe_rotate_mod']} | {p_asr[2]:.2%} | {p_asr[-1]:.2%} | {first_suspect(probe)} | {probe['state_audit']['round_5_client_1_included_layers']} |",
        "",
        "解释：两组均使用 4 客户端、6 轮、C1 在第 3 轮启动的强后门校准；该表只支持探针条件敏感性，不支持未知触发器泛化结论。",
    ]
    output = "\n".join(lines) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    print(output, end="")


if __name__ == "__main__":
    main()
