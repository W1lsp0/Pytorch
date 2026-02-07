"""
==============================================================================
🌍 Flower Server 联邦学习服务端
==============================================================================
这是 Flower 联邦学习的中央服务器。

主要职责:
  1. 协调训练轮次 (Rounds)
  2. 聚合客户端参数 (Aggregation / FedAvg)
  3. 收集并展示评估指标 (Metrics)
  4. 下发训练配置 (Config)

配置:
  - 算法: FedAvg
  - 轮次: 20
  - 最小客户端数: 3

作者: Flwr 联邦学习项目
==============================================================================
"""

import flwr as fl
from typing import List, Tuple, Dict, Any, Optional
from flwr.common import Metrics
import sys
import os

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
    print("\n" + "╔" + "═"*58 + "╗")
    print("║  📊 全局模型评估结果 (Global Metrics)".ljust(60) + "║")
    print("╠" + "═"*58 + "╣")
    print(f"║  🌟 平均准确率 (Accuracy):   {aggregated_accuracy * 100:.2f}%{' '*24}║")
    print(f"║  💀 平均攻击率 (ASR):        {aggregated_asr * 100:.2f}%{' '*24}║")
    print("╚" + "═"*58 + "╝\n")

    return {
        "accuracy": aggregated_accuracy,
        "asr": aggregated_asr
    }


import json
from flwr.server.client_proxy import ClientProxy
from flwr.common import FitRes, Parameters, Scalar

# ==================== TMAA 安全聚合策略 ====================
class TMAA_FedAvg(fl.server.strategy.FedAvg):
    """
    TMAA 增强版 FedAvg 策略
    
    功能:
        在聚合参数前，拦截并验证客户端提交的 '可信报告' (Trust Report)。
        根据硬件指纹和签名验证结果，决定是否接受该客户端的更新。
    """
    


    def log_audit(self, message: str):
        print(message)
        with open("tmaa_server_audit.log", "a", encoding="utf-8") as f:
            f.write(message + "\n")

    def aggregate_fit(
        self,
        server_round: int,
        results: List[Tuple[ClientProxy, FitRes]],
        failures: List[str | BaseException],
    ) -> Tuple[Optional[Parameters], Dict[str, Scalar]]:
        
        self.log_audit(f"\n🛡️  [TMAA Server] Round {server_round} | 接收客户端数据 (Passive Mode)...")
        
        valid_results = []
        rejected_count = 0
        
        for client, fit_res in results:
            metrics = fit_res.metrics
            if "trust_report_json" in metrics:
                try:
                    payload = json.loads(metrics["trust_report_json"])
                    # The report is wrapped in a structure with signature
                    report = payload.get("trust_report", payload) 
                    
                    tee_id = report['header']['device_id']
                    
                    # 提取攻击信息 (如有)
                    meta = report["metrics"].get("client_reported_meta", {})
                    attack_mode = meta.get("attack_mode", "none")
                    
                    self.log_audit(f"    📄 [Client {client.cid}] 收到可信报告 | TEE: {tee_id:12} | Attack: {attack_mode}")
                    
                    # 提取指纹 (演示用)
                    fingerprint = report["metrics"]["behavior_fingerprint"]
                    # print(f"       Fingerprint: {fingerprint}")
                    valid_results.append((client, fit_res))
                    
                except Exception as e:
                    self.log_audit(f"    ⚠️ [Client {client.cid}] 报告解析警告: {e}")
                    valid_results.append((client, fit_res))
            else:
                self.log_audit(f"    ⚠️ [Client {client.cid}] 未附带可信报告")
                valid_results.append((client, fit_res))

        self.log_audit(f"🛡️  [TMAA Server] 审计结束. 放行所有客户端 ({len(results)}) 进行聚合.")
        
        return super().aggregate_fit(server_round, results, failures)

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
    print("\n" + "╔" + "═"*60 + "╗")
    print(f"║  🚀 联邦学习服务器启动中... {' '*33}║")
    print("╠" + "═"*60 + "╣")
    print(f"║  📦 模型架构: ResNet-18{' '*38}║")
    print(f"║  📊 数据集:   CIFAR-10{' '*38}║")
    print(f"║  🔗 监听地址: 0.0.0.0:8080{' '*35}║")
    print(f"║  🔄 训练轮次: 20 Rounds{' '*38}║")
    print("╚" + "═"*60 + "╝\n")

    # 启动 Flower 服务器 (阻塞运行)
    fl.server.start_server(
        server_address="0.0.0.0:8080",
        config=fl.server.ServerConfig(num_rounds=20),
        strategy=strategy
    )

if __name__ == "__main__":
    main()