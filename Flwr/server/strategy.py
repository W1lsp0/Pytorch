
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

        # 3. Check Volatility (Training Fingerprint)
        # Verify that computation actually happened (Gaussian Noise / Random Weight Attack Detection)
        
        gpu_vol = fingerprint.get("gpu_volatility", 0.0)
        cpu_vol = fingerprint.get("cpu_volatility", 0.0)
        device_type = settings.get("device_type", "cpu").lower()
        
        # [L4] Gaussian Noise / Fake Training Check
        # Rule: Real training causes volatility > 0.
        if "cuda" in device_type:
             # GPU Training must show volatility. 
             # Threshold 0.01 allows for some idle time but filters pure noise/idling.
             if gpu_vol < 0.01:
                 return False, f"❌ Fake Training Detected (GPU Volatility {gpu_vol:.3f} too low)"
        else:
             # CPU Training must show volatility.
             if cpu_vol < 0.05: # CPU usually fluctuates more
                 return False, f"❌ Fake Training Detected (CPU Volatility {cpu_vol:.3f} too low)"
                 
        # 4. Check Data Health (Basic L3)

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
        
        # [Step 1] Pre-scan: Collect all trust reports & Model Updates for Cross-Client Analysis
        client_reports = {} # cid -> report
        initial_losses = []
        
        # L4 Sign Flipping: Collect flattened updates
        all_updates = [] # List[np.ndarray]
        client_update_map = {} # cid -> np.ndarray
        
        import numpy as np
        
        for client, fit_res in results:
            # 1. Collect Report
            if "trust_report_json" in fit_res.metrics:
                try:
                    payload = json.loads(fit_res.metrics["trust_report_json"])
                    report = payload.get("trust_report", payload)
                    client_reports[client.cid] = report
                    
                    # Collect Initial Loss for L4 Analysis
                    data_audit = report["metrics"].get("data_health_audit", {})
                    init_loss = data_audit.get("initial_loss", None)
                    if init_loss is not None:
                        initial_losses.append(init_loss)
                        
                except:
                    pass
            
            # 2. Collect Model Parameters (Flattened)
            # fit_res.parameters is Parameters(tensors=[bytes]), we need to deserialize
            try:
                # Deserialize to List[np.ndarray]
                weights = fl.common.parameters_to_ndarrays(fit_res.parameters)
                # Flatten all layers into a single vector
                flat_update = np.concatenate([w.flatten() for w in weights])
                all_updates.append(flat_update)
                client_update_map[client.cid] = flat_update
            except Exception as e:
                self.audit_logger.log(f"    ⚠️ [Client {client.cid}] Params deserialize failed: {e}")

        # Calculate Global Stats for L4 Policy
        median_loss = np.median(initial_losses) if initial_losses else 0.0
        mad_loss = np.median(np.abs(np.array(initial_losses) - median_loss)) if initial_losses else 0.0
        mad_loss = max(mad_loss, 1e-6)
        
        # [L4] Scaling Attack: Calculate Median Norm
        all_norms = [np.linalg.norm(u) for u in all_updates]
        median_norm = np.median(all_norms) if all_norms else 1.0
        norm_threshold = median_norm * 2.0
        if median_norm < 1e-4: norm_threshold = 1.0 # Avoid clipping if everyone starts near 0 discrepancy
        
        # Calculate Average Update Vector (pseudo-gradient direction)
        avg_update_vector = None
        global_grad_norm = 0.0
        if all_updates:
            # Mean of all updates (Reference Direction)
            avg_update_vector = np.mean(all_updates, axis=0)
            global_grad_norm = np.linalg.norm(avg_update_vector) + 1e-9
        
        self.audit_logger.log(f"    📊 [L4 Analysis] Global InitLoss: Med={median_loss:.4f} | Global Norm: Med={median_norm:.2f} (Clip > {norm_threshold:.2f})")

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
                    is_compliant, reason = self.policy_engine.check_compliance(report)
                    
                    l4_status = ""
                    
                    # [L4 Check 1] Initial Loss Consistency
                    data_audit = report["metrics"].get("data_health_audit", {})
                    # Fix: Handle NoneType if initial_loss is null in JSON
                    my_init_loss = data_audit.get("initial_loss")
                    if my_init_loss is None: my_init_loss = 0.0
                    
                    loss_deviation = abs(my_init_loss - median_loss) / (mad_loss + 1e-9)
                    
                    if loss_deviation > 3.0: 
                        l4_status += f" ⚠️ InitLoss Outlier (+{loss_deviation:.1f}σ)"
                    
                    # [L4 Check 2] Layer-wise Norm Filtering
                    client_meta = report["metrics"].get("client_reported_meta", {})
                    layer_updates = client_meta.get("layer_updates", [])
                    # Fix: Filter out None values in list
                    if layer_updates:
                        layer_updates = [x for x in layer_updates if x is not None]

                    if layer_updates and len(layer_updates) > 2:
                        extractor_norm = np.mean(layer_updates[:-2]) + 1e-9
                        classifier_norm = layer_updates[-1]
                        impact_ratio = classifier_norm / extractor_norm
                        if impact_ratio > 10.0:
                             l4_status += f" ⚠️ Head-Heavy (Ratio {impact_ratio:.1f})"

                    # [L4 Check 3] Cosine Similarity (Sign Flipping)
                    my_update = client_update_map.get(client.cid)
                    my_norm = 0.0
                    
                    if my_update is not None and avg_update_vector is not None:
                        # Cosine Sim = (A . B) / (|A| * |B|)
                        my_norm = np.linalg.norm(my_update) + 1e-9
                        dot_prod = np.dot(my_update, avg_update_vector)
                        cosine_sim = dot_prod / (my_norm * global_grad_norm)
                        
                        if cosine_sim < -0.5:
                            l4_status += f" ⚠️ Sign Flip Warn (Cos={cosine_sim:.2f})"

                        # [L4 Check 4] Zero Gradient (Lazy Client)
                        if my_norm < 1e-4:
                             l4_status += f" ❌ Zero Grad (Lazy)"
                        
                        # [L4 Check 5] Scaling Attack (Norm Consistency & Clipping)
                        # Part A: Consistency (Did they lie?)
                        if layer_updates:
                             # Reported Norm = sqrt(sum(layer_update^2))
                             reported_norm = np.sqrt(np.sum(np.array(layer_updates)**2))
                             # Allow some floating point error (e.g. 5%)
                             if abs(my_norm - reported_norm) > (my_norm * 0.1) + 1e-3:
                                  l4_status += f" ⚠️ Norm Mismatch (Act={my_norm:.2f}|Rep={reported_norm:.2f})"
                        
                        # Part B: Norm Clipping (Global Median Threshold)
                        if my_norm > norm_threshold:
                            l4_status += f" 🛡️  Clipped (Norm {my_norm:.1f}->{norm_threshold:.1f})"
                            # Perform Clipping
                            scale_factor = norm_threshold / my_norm
                            try:
                                # Deserialize, Scale, Reserialize
                                ndarrays = fl.common.parameters_to_ndarrays(fit_res.parameters)
                                scaled_ndarrays = [layer * scale_factor for layer in ndarrays]
                                fit_res.parameters = fl.common.ndarrays_to_parameters(scaled_ndarrays)
                            except Exception as e:
                                l4_status += f" (Clip Failed: {e})"
                    
                    status_icon = "✅" if is_compliant else "⚠️"
                    client_logs.append(f"    📄 [Client {client.cid}] TEE: {tee_id[:8]}.. | {status_icon} Policy: {reason}{l4_status}")

                    # [New Feature] 记录数据统计特征 (Data Fingerprint Logging)
                    cluster_q = data_audit.get("cluster_quality")
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
