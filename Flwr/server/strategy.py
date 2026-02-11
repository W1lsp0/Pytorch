
import flwr as fl
from typing import List, Tuple, Dict, Any, Optional
from flwr.server.client_proxy import ClientProxy
from flwr.common import FitRes, Parameters, Scalar
import json

from audit import AuditLogger

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

        # 3. Check GPU Volatility (GPU 行为异常检测)
        # 如果 GPU 波动率为 0 但声称使用了 CUDA，可能是假训练
        gpu_vol = fingerprint.get("gpu_volatility", -1)
        client_meta = metrics.get("client_reported_meta", {})
        device_type = client_meta.get("device_type", "cpu")
        if "cuda" in device_type and gpu_vol == 0.0:
            return False, "⚠️ GPU volatility is zero despite CUDA training (Possible Fake)"

        # 4. Check Data Quality (Inspector) -> Optional
        # e.g. Reject if Entropy is too low (Data Poisoning / Lazy)
        # data_audit = metrics.get("data_health_audit", {})
        
        return True, "✅ Compliant"


# ==================== TMAA 安全聚合策略 ====================
class TMAA_FedAvg(fl.server.strategy.FedAvg):
    """
    TMAA 增强版 FedAvg 策略
    
    功能:
        在聚合参数前，拦截并验证客户端提交的 '可信报告' (Trust Report)。
        根据硬件指纹和签名验证结果，决定是否接受该客户端的更新。
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.policy_engine = PolicyMatcher()
        self.audit_logger = AuditLogger()

    def aggregate_fit(
        self,
        server_round: int,
        results: List[Tuple[ClientProxy, FitRes]],
        failures: List[str | BaseException],
    ) -> Tuple[Optional[Parameters], Dict[str, Scalar]]:
        
        self.audit_logger.log(f"\n🛡️  [TMAA Server] Round {server_round} | 接收客户端数据 (Passive Mode)...")
        
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
                    
                    # Policy Check (策略检查)
                    is_compliant, reason = self.policy_engine.check_compliance(report)
                    
                    status_icon = "✅" if is_compliant else "⚠️"
                    self.audit_logger.log(f"    📄 [Client {client.cid}] TEE: {tee_id[:8]}.. | {status_icon} Policy: {reason}")

                    # [Strict Enforcement Switch]
                    # 目前仅记录日志，不实际拒绝 (Simulation Mode)
                    # if not is_compliant:
                    #     self.audit_logger.log(f"       ⛔ 拒绝聚合: 违反安全策略")
                    #     rejected_count += 1
                    #     continue

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
                        
                    self.audit_logger.log(f"       📊 Data Fingerprint: Dist={dist_str} | Feat={feat_sum}")
                    
                    # 记录资源摘要 (v2.0 新增)
                    resource_sum = report["metrics"].get("resource_summary", {})
                    if resource_sum:
                        self.audit_logger.log(
                            f"       🖥️  Resources: CPU={resource_sum.get('avg_cpu', '?')}% "
                            f"GPU={resource_sum.get('avg_gpu', '?')}% "
                            f"Mem={resource_sum.get('avg_memory_mb', '?')}MB "
                            f"Temp={resource_sum.get('avg_temperature_c', '?')}°C "
                            f"({resource_sum.get('sample_count', '?')} samples)"
                        )
                    
                    # [New Feature] 客户端 0 独立审计日志 (Isolated Logging for Client 0)
                    self.audit_logger.log_client_event(client.cid, tee_id, server_round, report)
                            
                    valid_results.append((client, fit_res))
                    
                except Exception as e:
                    self.audit_logger.log(f"    ⚠️ [Client {client.cid}] 报告解析警告: {e}")
                    valid_results.append((client, fit_res))
            else:
                self.audit_logger.log(f"    ⚠️ [Client {client.cid}] 未附带可信报告")
                valid_results.append((client, fit_res))

        self.audit_logger.log(f"🛡️  [TMAA Server] 审计结束. 放行所有客户端 ({len(results)}), 拒绝 ({rejected_count}).")
        
        return super().aggregate_fit(server_round, results, failures)
