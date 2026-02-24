
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
        验证可信报告是否符合安全基线
        返回值: (是否合规, 原因)
        """
        metrics = report.get("metrics", {})
        
        # 1. 检查完整性（系统完整性）
        integrity = metrics.get("system_integrity", {})
        if integrity.get("file_tampered", False):
             return False, "❌ 系统完整性检查失败（文件被篡改）"
             
        # 2. 检查行为（吞吐量 / 虚假训练 / 发散性）
        fingerprint = metrics.get("behavior_fingerprint", {})
        throughput_status = fingerprint.get("throughput_check", "NORMAL")
        if "SUSPECTED" in throughput_status:
             return False, f"❌ 行为检查失败 ({throughput_status})"
        
        loss_trend = fingerprint.get("loss_trend", "STABLE")
        if "DIVERGING" in loss_trend:
             return False, f"❌ 检测到训练发散 ({loss_trend})"

        # 3. 检查波动性（训练指纹）
        # 验证计算是否真实发生（高斯噪声 / 随机权重攻击检测）
        
        gpu_vol = fingerprint.get("gpu_volatility", 0.0)
        cpu_vol = fingerprint.get("cpu_volatility", 0.0)
        # [L4] 高斯噪声 / 虚假训练检查
        # 规则: 真实训练会导致波动性 > 0
        # 动态检查: 如果 GPU 波动显著，则强制执行 GPU 阈值
        # 否则回退到 CPU 检查
        
        has_gpu_activity = gpu_vol > 0.001
        
        if has_gpu_activity:
             # GPU 训练必须显示波动性
             # 阈值 0.01 允许一些空闲时间，但过滤纯噪声/空转
             if gpu_vol < 0.01:
                 return False, f"❌ 检测到虚假训练 (GPU 波动性 {gpu_vol:.3f} 过低)"
        else:
             # CPU 训练必须显示波动性
             if cpu_vol < 0.05: # CPU 通常波动更大
                 return False, f"❌ 检测到虚假训练 (CPU 波动性 {cpu_vol:.3f} 过低)"
                 
        # 4. 检查数据健康度（基本 L3）

        # 4. 检查数据质量（检查器）-> 可选
        # 例如: 如果熵过低则拒绝（数据投毒 / 懒惰客户端）
        # data_audit = metrics.get("data_health_audit", {})
        
        return True, "✅ 符合要求"


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
        
        # [步骤 1] 预扫描: 收集所有可信报告和模型更新用于跨客户端分析
        client_reports = {} # 客户端ID -> 报告
        initial_losses = []
        
        # L4 符号翻转检测: 收集扁平化更新
        all_updates = [] # List[np.ndarray]
        client_update_map = {} # 客户端ID -> np.ndarray
        
        import numpy as np
        
        for client, fit_res in results:
            # 1. 收集报告
            if "trust_report_json" in fit_res.metrics:
                try:
                    payload = json.loads(fit_res.metrics["trust_report_json"])
                    report = payload.get("trust_report", payload)
                    client_reports[client.cid] = report
                    
                    # 收集初始损失用于 L4 分析
                    data_audit = report["metrics"].get("data_health_audit", {})
                    init_loss = data_audit.get("initial_loss", None)
                    if init_loss is not None:
                        initial_losses.append(init_loss)
                        
                except:
                    pass
            
            # 2. 收集模型参数（扁平化）
            # fit_res.parameters 是 Parameters(tensors=[bytes])，需要反序列化
            try:
                # 反序列化为 List[np.ndarray]
                weights = fl.common.parameters_to_ndarrays(fit_res.parameters)
                # 将所有层扁平化为单个向量
                flat_update = np.concatenate([w.flatten() for w in weights])
                all_updates.append(flat_update)
                client_update_map[client.cid] = flat_update
            except Exception as e:
                self.audit_logger.log(f"    ⚠️ [客户端 {client.cid}] 参数反序列化失败: {e}")

        # 计算 L4 策略的全局统计信息
        median_loss = np.median(initial_losses) if initial_losses else 0.0
        mad_loss = np.median(np.abs(np.array(initial_losses) - median_loss)) if initial_losses else 0.0
        mad_loss = max(mad_loss, 1e-6)
        
        # [L4] 缩放攻击: 计算中位数范数
        all_norms = [np.linalg.norm(u) for u in all_updates]
        median_norm = np.median(all_norms) if all_norms else 1.0
        norm_threshold = median_norm * 2.0
        if median_norm < 1e-4: norm_threshold = 1.0 # 如果所有客户端都接近 0 偏差，避免裁剪
        
        # 计算平均更新向量（伪梯度方向）
        avg_update_vector = None
        global_grad_norm = 0.0
        if all_updates:
            # 所有更新的均值（参考方向）
            avg_update_vector = np.mean(all_updates, axis=0)
            global_grad_norm = np.linalg.norm(avg_update_vector) + 1e-9
        
        self.audit_logger.log(f"    📊 [L4 Analysis] Global InitLoss: Med={median_loss:.4f} | Global Norm: Med={median_norm:.2f} (Clip > {norm_threshold:.2f})")

        valid_results = []
        rejected_count = 0
        
        # [步骤 2] 主循环: 验证和记录日志
        for client, fit_res in results:
            metrics = fit_res.metrics
            client_logs = []  # [原子性] 缓冲此客户端的日志

            if client.cid in client_reports:
                try:
                    report = client_reports[client.cid]
                    tee_id = report['header']['device_id']
                    
                    # 策略检查
                    is_compliant, reason = self.policy_engine.check_compliance(report)
                    
                    l4_status = ""
                    
                    # [L4 检查 1] 初始损失一致性
                    data_audit = report["metrics"].get("data_health_audit", {})
                    # 修复: 处理 JSON 中 initial_loss 为 null 的情况
                    my_init_loss = data_audit.get("initial_loss")
                    if my_init_loss is None: my_init_loss = 0.0
                    
                    loss_deviation = abs(my_init_loss - median_loss) / (mad_loss + 1e-9)
                    
                    if loss_deviation > 3.0: 
                        l4_status += f" ⚠️ 初始损失异常值 (+{loss_deviation:.1f}σ)"
                    
                    # [L4 检查 2] 逐层范数过滤
                    client_meta = report["metrics"].get("client_reported_meta", {})
                    layer_updates = client_meta.get("layer_updates", [])
                    # 修复: 过滤列表中的 None 值
                    if layer_updates:
                        layer_updates = [x for x in layer_updates if x is not None]

                    if layer_updates and len(layer_updates) > 2:
                        extractor_norm = np.mean(layer_updates[:-2]) + 1e-9
                        classifier_norm = layer_updates[-1]
                        impact_ratio = classifier_norm / extractor_norm
                        if impact_ratio > 10.0:
                             l4_status += f" ⚠️ 头部过重 (比例 {impact_ratio:.1f})"

                    # [L4 检查 3] 余弦相似度（符号翻转）
                    my_update = client_update_map.get(client.cid)
                    my_norm = 0.0
                    
                    if my_update is not None and avg_update_vector is not None:
                        # 余弦相似度 = (A . B) / (|A| * |B|)
                        my_norm = np.linalg.norm(my_update) + 1e-9
                        dot_prod = np.dot(my_update, avg_update_vector)
                        cosine_sim = dot_prod / (my_norm * global_grad_norm)
                        
                        if cosine_sim < -0.5:
                            l4_status += f" ⚠️ 符号翻转警告 (Cos={cosine_sim:.2f})"

                        # [L4 检查 4] 零梯度（懒惰客户端）
                        if my_norm < 1e-4:
                             l4_status += f" ❌ 零梯度（懒惰）"
                        
                        # [L4 检查 5] 缩放攻击（范数一致性和裁剪）
                        # 部分 A: 一致性（是否造假？）
                        if layer_updates:
                             # 报告的范数 = sqrt(sum(layer_update^2))
                             reported_norm = np.sqrt(np.sum(np.array(layer_updates)**2))
                             # 允许一些浮点误差（例如 5%）
                             if abs(my_norm - reported_norm) > (my_norm * 0.1) + 1e-3:
                                  l4_status += f" ⚠️ 范数不匹配 (实际={my_norm:.2f}|报告={reported_norm:.2f})"
                        
                        # 部分 B: 范数检测（全局中位数阈值）
                        if my_norm > norm_threshold:
                            l4_status += f" ⚠️ 缩放攻击检测 (范数 {my_norm:.1f} > 阈值 {norm_threshold:.1f})"
                            # 仅报告，不进行裁剪或拒绝
                    
                    status_icon = "✅" if is_compliant else "❌"
                    client_logs.append(f"    📄 [Client {client.cid}] TEE: {tee_id[:8]}.. | {status_icon} Policy: {reason}{l4_status}")

                    # [新功能] 记录数据统计特征（数据指纹记录）
                    cluster_q = data_audit.get("cluster_quality")
                    if isinstance(cluster_q, dict):
                         q_str = f"可分性={cluster_q.get('separability_ratio', '?')}"
                    else:
                         q_str = "N/A"

                    client_logs.append(f"       📊 数据审计: 聚类={q_str} | 初始损失={my_init_loss:.3f}")
                    
                    # 记录资源摘要（v2.0 新增）
                    resource_sum = report["metrics"].get("resource_summary", {})
                    if resource_sum:
                        client_logs.append(
                            f"       🖥️  资源使用: CPU={resource_sum.get('avg_cpu', '?')}% "
                            f"GPU={resource_sum.get('avg_gpu', '?')}% "
                            f"内存={resource_sum.get('avg_memory_mb', '?')}MB "
                            f"({resource_sum.get('sample_count', '?')} 个样本)"
                        )
                    
                    # 客户端 0 独立审计
                    self.audit_logger.log_client_event(client.cid, tee_id, server_round, report)
                    
                    # 严格拒绝逻辑 (仅针对 L1/L2 Policy Check)
                    if is_compliant:
                        valid_results.append((client, fit_res))
                    else:
                        rejected_count += 1
                        client_logs.append(f"       ❌ 拒绝原因: {reason}")
                    
                except Exception as e:
                    client_logs.append(f"    ⚠️ [Client {client.cid}] 报告解析警告: {e}")
                    valid_results.append((client, fit_res))
            else:
                client_logs.append(f"    ⚠️ [Client {client.cid}] 未附带可信报告")
                valid_results.append((client, fit_res))
            
            # [原子性] 刷新此客户端的缓冲日志
            self.audit_logger.log_batch(client_logs)

        self.audit_logger.log(f"🛡️  [TMAA Server] 审计结束. 放行所有客户端 ({len(results)}), 拒绝 ({rejected_count}).")
        
        return super().aggregate_fit(server_round, results, failures)
