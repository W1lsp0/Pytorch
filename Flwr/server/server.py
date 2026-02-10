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
    


# ==================== TMAA 策略引擎 (Policy Engine) ====================
class PolicyMatcher:
    """
    TMAA 安全策略匹配器
    理论对应: 阶段一 (准入) - 严格策略执行
    """
    def check_compliance(self, report: Dict[str, Any]) -> Tuple[bool, str]:
        """
        验证 Trust Report 是否符合安全基线
        Returns: (is_compliant, reason)
        """
        metrics = report.get("metrics", {})
        
        # 1. Check Integrity (系统完整性)
        integrity = metrics.get("system_integrity", {})
        if integrity.get("file_tampered", False):
             return False, "❌ System integrity check failed (File Tampered)"
             
        # 2. Check Behavior (Throughput / Fake Training / Divergence)
        fingerprint = metrics.get("behavior_fingerprint", {})
        throughput_status = fingerprint.get("throughput_check", "NORMAL")
        if "SUSPECTED" in throughput_status:
             return False, f"❌ Behavior check failed ({throughput_status})"
        
        loss_trend = fingerprint.get("loss_trend", "STABLE")
        if "DIVERGING" in loss_trend:
             return False, f"❌ Training Divergence Detected ({loss_trend})"

        # 3. Check Data Quality (Inspector) -> Optional
        # e.g. Reject if Entropy is too low (Data Poisoning / Lazy)
        # data_audit = metrics.get("data_health_audit", {})
        
        return True, "✅ Compliant"

# ==================== TMAA 安全聚合策略 ====================
class TMAA_FedAvg(fl.server.strategy.FedAvg):
    """
    TMAA 增强版 FedAvg 策略
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.policy_engine = PolicyMatcher()

    def log_audit(self, message: str):
        print(message, flush=True)
        # 确保 log 目录存在 (虽然 run_simulation.sh 已创建，但 Server 可能独立运行)
        os.makedirs("log", exist_ok=True)
        with open("log/tmaa_server_audit.log", "a", encoding="utf-8") as f:
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
                    
                    # Policy Check (策略检查)
                    is_compliant, reason = self.policy_engine.check_compliance(report)
                    
                    status_icon = "✅" if is_compliant else "⚠️"
                    self.log_audit(f"    📄 [Client {client.cid}] TEE: {tee_id[:8]}.. | {status_icon} Policy: {reason}")

                    # [Strict Enforcement Switch]
                    # 目前仅记录日志，不实际拒绝 (Simulation Mode)
                    # if not is_compliant:
                    #     self.log_audit(f"       ⛔ 拒绝聚合: 违反安全策略")
                    #     rejected_count += 1
                    #     continue

                    # 提取指纹 (演示用)
                    fingerprint = report["metrics"]["behavior_fingerprint"]
                    # print(f"       Fingerprint: {fingerprint}")
                    
                    # [New Feature] 记录数据统计特征 (Data Fingerprint Logging)
                    data_audit = report["metrics"].get("data_health_audit", {})
                    label_dist = data_audit.get("label_distribution", "N/A")
                    feat_sum = data_audit.get("feature_summary", "N/A")
                    
                    # 简化日志输出
                    if isinstance(label_dist, dict):
                        # 只显示非零类别，节省日志空间
                        dist_str = {k: v for k, v in label_dist.items() if v > 0}
                    else:
                        dist_str = "N/A"
                        
                    self.log_audit(f"       📊 Data Fingerprint: Dist={dist_str} | Feat={feat_sum}")
                    
                    # [New Feature] 客户端 0 独立审计日志 (Isolated Logging for Client 0)
                    # 识别 Client 0 (Client ID=0 -> worker_0000)
                    if "worker_0000" in tee_id or str(client.cid) == "0":
                        audit_entry = {
                            "round": server_round,
                            "timestamp": datetime.now().isoformat(),
                            "report": report
                        }
                        
                        client0_log_path = "log/client_0_history.json"
                        
                        # 为了保持 JSON 格式合法，我们需要读取-更新-写入，或者使用 JSON Lines
                        # 这里使用简单的追加+分隔符方式，或者追加 list (效率低但可读)
                        # 采用追加 JSON Lines 格式 (.jsonl)，每行一个 JSON 对象
                        with open("log/client_0_audit.jsonl", "a", encoding="utf-8") as f0:
                            f0.write(json.dumps(audit_entry, ensure_ascii=False) + "\n")
                            
                    valid_results.append((client, fit_res))
                    
                except Exception as e:
                    self.log_audit(f"    ⚠️ [Client {client.cid}] 报告解析警告: {e}")
                    valid_results.append((client, fit_res))
            else:
                self.log_audit(f"    ⚠️ [Client {client.cid}] 未附带可信报告")
                valid_results.append((client, fit_res))

        self.log_audit(f"🛡️  [TMAA Server] 审计结束. 放行所有客户端 ({len(results)}), 拒绝 ({rejected_count}).")
        
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