
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
        
        # [Step 1] Pre-scan: Collect all trust reports to calculate Global Stats (L4 Cross-Client Analysis)
        client_reports = {} # cid -> report
        initial_losses = []
        
        for client, fit_res in results:
            if "trust_report_json" in fit_res.metrics:
                try:
                    payload = json.loads(fit_res.metrics["trust_report_json"])
                    report = payload.get("trust_report", payload)
                    client_reports[client.cid] = report
                    
                    # Collect Initial Loss for L4 Analysis
                    # Path: metrics -> client_reported_meta -> training_curve (list of dicts) -> [0]['loss']
                    # Or check 'data_health_audit' -> 'initial_loss' (from inspector)
                    # Let's prefer 'data_health_audit' as it's signed from Inspector
                    data_audit = report["metrics"].get("data_health_audit", {})
                    init_loss = data_audit.get("initial_loss", None)
                    if init_loss is not None:
                        initial_losses.append(init_loss)
                        
                except:
                    pass
        
        # Calculate Global Stats for L4 Policy
        import numpy as np
        median_loss = np.median(initial_losses) if initial_losses else 0.0
        mad_loss = np.median(np.abs(np.array(initial_losses) - median_loss)) if initial_losses else 0.0
        # Avoid division by zero
        mad_loss = max(mad_loss, 1e-6)
        
        self.audit_logger.log(f"    📊 [L4 Analysis] Global Initial Loss: Median={median_loss:.4f}, MAD={mad_loss:.4f}")

        valid_results = []
        rejected_count = 0
        
        # [Step 2] Main Loop: Validate and Log
        for client, fit_res in results:
            metrics = fit_res.metrics
            client_logs = []  # [Atomic] Buffer logs for this client

            if client.cid in client_reports:
                try:
                    report = client_reports[client.cid]
                    tee_id = report['header']['device_id']
                    
                    # Policy Check (策略检查)
                    # Now passing global stats to check_compliance if needed, or check externally
                    is_compliant, reason = self.policy_engine.check_compliance(report)
                    
                    # [L4 Check] Initial Loss Consistency (Is this client an outlier?)
                    data_audit = report["metrics"].get("data_health_audit", {})
                    my_init_loss = data_audit.get("initial_loss", 0.0)
                    loss_deviation = abs(my_init_loss - median_loss) / mad_loss
                    
                    l4_status = ""
                    if loss_deviation > 3.0: # > 3 MADs
                        l4_status += f" ⚠️ InitLoss Outlier (+{loss_deviation:.1f}σ)"
                        # is_compliant = False # Optional: Enforce strict
                    
                    # [L4 Check] Layer-wise Norm Filtering
                    # Check for "Head-Heavy" updates (Classifier >> Extractor)
                    client_meta = report["metrics"].get("client_reported_meta", {})
                    layer_updates = client_meta.get("layer_updates", [])
                    if layer_updates and len(layer_updates) > 2:
                        # Simple heuristic: Last layer vs Mean of first few layers
                        extractor_norm = np.mean(layer_updates[:-2]) + 1e-9
                        classifier_norm = layer_updates[-1]
                        impact_ratio = classifier_norm / extractor_norm
                        
                        if impact_ratio > 10.0: # Heuristic threshold
                             l4_status += f" ⚠️ Head-Heavy Update (Ratio {impact_ratio:.1f})"
                    
                    status_icon = "✅" if is_compliant else "⚠️"
                    client_logs.append(f"    📄 [Client {client.cid}] TEE: {tee_id[:8]}.. | {status_icon} Policy: {reason}{l4_status}")

                    # [New Feature] 记录数据统计特征 (Data Fingerprint Logging)
                    # Extract Cluster Quality (L3)
                    cluster_q = data_audit.get("cluster_quality", "N/A")
                    if isinstance(cluster_q, dict):
                         q_str = f"Sep={cluster_q.get('separability_ratio', '?')}"
                    else:
                         q_str = "N/A"

                    client_logs.append(f"       📊 Data Audit: Cluster={q_str} | InitLoss={my_init_loss:.3f}")
                    
                    # 记录资源摘要 (v2.0 新增)
                    resource_sum = report["metrics"].get("resource_summary", {})
                    if resource_sum:
                        client_logs.append(
                            f"       🖥️  Resources: CPU={resource_sum.get('avg_cpu', '?')}% "
                            f"GPU={resource_sum.get('avg_gpu', '?')}% "
                            f"Mem={resource_sum.get('avg_memory_mb', '?')}MB "
                            f"({resource_sum.get('sample_count', '?')} samples)"
                        )
                    
                    # Client 0 Independent Audit
                    self.audit_logger.log_client_event(client.cid, tee_id, server_round, report)
                            
                    valid_results.append((client, fit_res))
                    
                except Exception as e:
                    client_logs.append(f"    ⚠️ [Client {client.cid}] 报告解析警告: {e}")
                    valid_results.append((client, fit_res))
            else:
                client_logs.append(f"    ⚠️ [Client {client.cid}] 未附带可信报告")
                valid_results.append((client, fit_res))
            
            # [Atomic] Flush buffered logs for this client
            self.audit_logger.log_batch(client_logs)

        self.audit_logger.log(f"🛡️  [TMAA Server] 审计结束. 放行所有客户端 ({len(results)}), 拒绝 ({rejected_count}).")
        
        return super().aggregate_fit(server_round, results, failures)
