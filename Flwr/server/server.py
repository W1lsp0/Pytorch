"""
==============================================================================
🌍 Flower Server 联邦学习服务端 (Entry Point)
==============================================================================
这是 Flower 联邦学习的中央服务器入口。

主要职责:
  1. 配置聚合策略 (TMAA_FedAvg)
  2. 启动 Flower Server
  3. 协调训练流程

配置:
  - 算法: FedAvg
  - 轮次: 20
  - 最小客户端数: 10

作者: Flwr 联邦学习项目
Refactored: 2026-02-11
==============================================================================
"""

import flwr as fl
from typing import List, Tuple
from flwr.common import Metrics
import sys

# 导入模块化组件
from strategy import TMAA_FedAvg

# ==================== 解决 Windows 中文乱码问题 ====================
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
# ================================================================

# ==================== 配置回调函数 ====================
def get_on_fit_config_fn(server_round: int):
    """
    配置函数：向客户端下发当前训练轮次信息
    客户端可以在 fit() 的 config 参数中读取到。
    """
    return {
        "current_round": server_round,
        "global_batch_size": 32, # 示例配置
    }


# ==================== 聚合回调函数 ====================
def weighted_average(metrics: List[Tuple[int, Metrics]]) -> Metrics:
    """
    聚合函数：处理客户端返回的 metrics
    
    计算:
        - 全局样本加权平均准确率 (Accuracy)
        - 全局样本加权平均后门成功率 (ASR)
        
    Args:
        metrics: list of (num_examples, metrics_dict)
    """
    total_examples = sum([num_examples for num_examples, _ in metrics])
    
    # 聚合 Accuracy
    weighted_accuracies = [num * m["accuracy"] for num, m in metrics]
    aggregated_accuracy = sum(weighted_accuracies) / total_examples

    # 聚合 ASR (如果存在)
    # 注意: 部分客户端可能没传这个字段，需要 safe get
    weighted_asrs = [num * m.get("asr", 0.0) for num, m in metrics]
    aggregated_asr = sum(weighted_asrs) / total_examples

    # 美化输出：显示全局指标
    # 原子输出 (防止多线程交错)
    print("\n".join([
        "",
        "╔" + "═"*58 + "╗",
        "║  📊 全局模型评估结果 (Global Metrics)".ljust(60) + "║",
        "╠" + "═"*58 + "╣",
        f"║  🌟 平均准确率 (Accuracy):   {aggregated_accuracy * 100:.2f}%{' '*24}║",
        f"║  💀 平均攻击率 (ASR):        {aggregated_asr * 100:.2f}%{' '*24}║",
        "╚" + "═"*58 + "╝",
        ""
    ]))

    return {
        "accuracy": aggregated_accuracy,
        "asr": aggregated_asr
    }

# ==================== 策略配置 ====================
# 使用 TMAA 自定义策略
strategy = TMAA_FedAvg(
    fraction_fit=1.0,                      # 每轮采样 100% 的可用客户端参与训练
    fraction_evaluate=1.0,                 # 每轮采样 100% 的可用客户端参与评估
    min_fit_clients=10,                     # 每轮至少请求 10 个客户端
    min_evaluate_clients=10,                # 每轮至少请求 10 个客户端
    min_available_clients=10,               # 启动训练前等待至少 10 个客户端连接
    
    evaluate_metrics_aggregation_fn=weighted_average,  # 配置聚合函数
    on_fit_config_fn=get_on_fit_config_fn,            # 配置下发函数
)


# ==================== 启动服务器 ====================
def main():
    # 原子输出 (防止多线程交错)
    print("\n".join([
        "",
        "╔" + "═"*60 + "╗",
        f"║  🚀 联邦学习服务器启动中... {' '*33}║",
        "╠" + "═"*60 + "╣",
        f"║  📦 模型架构: ResNet-18{' '*38}║",
        f"║  📊 数据集:   CIFAR-10{' '*38}║",
        f"║  🔗 监听地址: 0.0.0.0:8080{' '*35}║",
        f"║  🔄 训练轮次: 20 Rounds{' '*38}║",
        "╚" + "═"*60 + "╝",
        ""
    ]))

    # 启动 Flower 服务器 (阻塞运行)
    fl.server.start_server(
        server_address="0.0.0.0:8080",
        config=fl.server.ServerConfig(num_rounds=3),
        strategy=strategy
    )

if __name__ == "__main__":
    main()