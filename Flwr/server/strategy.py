import json
import math
import numpy as np
from collections import deque
from typing import List, Tuple, Dict, Optional

import flwr as fl
from flwr.common import Parameters, FitRes, Scalar, ndarrays_to_parameters, parameters_to_ndarrays
from flwr.server.client_proxy import ClientProxy

from audit import AuditLogger

# === 导入从 strategy.py 单独拆分出去的子模块 ===
from trust_manager import TrustScoreManager
from contribution import ContributionValidator
from sensitivity import calculate_layer_sensitivity, calculate_inclusion_threshold

# 为导入 Client 模块添加路径 (如果需要)
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Client'))
try:
    from model import get_resnet18
except ImportError:
    # 回退方案
    def get_resnet18(num_classes=10):
        import torchvision.models as models
        import torch.nn as nn
        net = models.resnet18(weights=None)
        net.conv1 = nn.Conv2d(3, 64, kernel_size=3, stride=1, padding=1, bias=False)
        net.maxpool = nn.Identity()
        net.fc = nn.Linear(net.fc.in_features, num_classes)
        return net


class TMAA_FedAvg(fl.server.strategy.FedAvg):
    """
    TMAA 增强版 FedAvg 策略：完全实现双流双层与动态门限
    本聚合引擎与传统 FedAvg 的最大差异在于，放弃了“一刀切”聚合，而是采用
    基于客户端历史声誉与节点设备健康审查的分层参数防投毒拦截算法。
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 初始化核心防御组件
        self.trust_manager = TrustScoreManager()
        self.contribution_validator = ContributionValidator()
        self.audit_logger = AuditLogger()

    def aggregate_fit(
        self,
        server_round: int,
        results: List[Tuple[ClientProxy, FitRes]],
        failures: List[str | BaseException],
    ) -> Tuple[Optional[Parameters], Dict[str, Scalar]]:
        
        self.audit_logger.log(f"\n🛡️  [TMAA Server] Round {server_round} | 审计阶段开始...")
        
        if not results:
            return None, {}

        client_data_map = {}
        client_logs = []
        rejected_count = 0
        
        # ==========================================================
        # 步骤 1: 基础解析与信任分评估 (Trust Assessment)
        # ==========================================================
        total_trust_score = 0.0
        g_ref_weighted_sum = None
        
        for client, fit_res in results:
            cid = client.cid
            
            # 解析安全报告 (TrustReport)
            report = {}
            if "trust_report_json" in fit_res.metrics:
                try:
                    payload = json.loads(fit_res.metrics["trust_report_json"])
                    report = payload.get("trust_report", payload)
                except Exception as e:
                    client_logs.append(f"    ⚠️ [Client {cid}] 报告解析失败: {e}")
                    
            if not report:
                rejected_count += 1
                client_logs.append(f"    ❌ [Client {cid}] 未提供可信报告，拦截")
                continue

            # 第一道防线：评估设备健康环境硬性门禁 
            m_attest, trust_score = self.trust_manager.evaluate_m_attest_and_trust(cid, report)
            if trust_score <= 0.0:
                rejected_count += 1
                client_logs.append(f"    ❌ [Client {cid}] 信任评估不通过，熔断拦截")
                continue

            # 获取由客户端提交的各个梯度矩阵的 Flatten() 形态
            try:
                weights = parameters_to_ndarrays(fit_res.parameters)
                flat_update = np.concatenate([w.flatten() for w in weights])
            except Exception as e:
                rejected_count += 1
                client_logs.append(f"    ❌ [Client {cid}] 权重解析失败: {e}")
                continue

            client_data_map[cid] = {
                "client_proxy": client,
                "fit_res": fit_res,
                "flat_update": flat_update,
                "weights": weights,
                "report": report,
                "trust_score": trust_score,
                "tee_id": report.get("device_info", {}).get("tee_id", "Unknown")
            }
            
            # 计算基线参考真理 (参照物) 时，基于当前该人的 TrustScore 进行声量加权！
            if g_ref_weighted_sum is None:
                g_ref_weighted_sum = flat_update * trust_score
            else:
                g_ref_weighted_sum += flat_update * trust_score
            
            total_trust_score += trust_score
            
        # 防止控制台日志重叠导致输出丢失
        self.audit_logger.log_batch(client_logs)
        client_logs.clear()

        if not client_data_map or total_trust_score == 0:
            self.audit_logger.log("    ❌ 本轮无有效客户端，中止。")
            return None, {}

        # ==========================================================
        # 步骤 2: 内容审查与得分加权一致性 (Content Scrutiny)
        # ==========================================================
        # 产生高信誉玩家主导的主基准梯度，抵抗普通女巫攻击同化
        g_ref = g_ref_weighted_sum / total_trust_score
        
        # 【模拟 Root G】 理想情况下应该有一个服务器私密的清洗良好的微型数据集测算
        # 如果没有独立数据集做测试，则使用刚刚汇聚出得加权共识作为真理衡量标准
        g_root = g_ref
        
        all_s_contents = []
        round_positive_sims = []

        for cid, data in client_data_map.items():
            g_k = data["flat_update"]
            
            # 衡量方向：与大众基准方向的一致程度
            norm_k = np.linalg.norm(g_k) + 1e-9
            norm_ref = np.linalg.norm(g_ref) + 1e-9
            cos_sim_ref = np.dot(g_k, g_ref) / (norm_k * norm_ref)
            # 使用 sqrt(ReLU) 抑制负向并激励正向
            s_consist = math.sqrt(max(0.0, cos_sim_ref))
            
            # 衡量贡献度：与代表模型演进正确客观方向的角度
            cos_sim_root = np.dot(g_k, g_root) / (norm_k * np.linalg.norm(g_root) + 1e-9)
            s_contrib = math.sqrt(max(0.0, cos_sim_root))
            
            if cos_sim_root > 0: round_positive_sims.append(cos_sim_root)
            
            # 双向几何平均数成为这一轮其提供的单纯“纯净的内容质量分” (不含资历情感)
            s_content = math.sqrt(s_consist * s_contrib)
            data["s_content"] = s_content
            all_s_contents.append(s_content)

        # ==========================================================
        # 步骤 3: 历史演进模块 (History Evolution)
        # ==========================================================
        mu_avg = np.mean(all_s_contents) if all_s_contents else 0.0
        sigma_scale = np.std(all_s_contents) + 1e-6
        
        # 调用分离出的 trust_manager 获取最终包含历史偏见的超级权重：CompositeWeight
        client_updates_for_manager = {cid: {"s_content": d["s_content"], "s_trust": d["trust_score"]} for cid, d in client_data_map.items()}
        raw_scores = self.trust_manager.update_history_and_get_weight(client_updates_for_manager, mu_avg, sigma_scale)
        
        # 将原始计算积分做 Softmax 或线性占比标准化缩放
        total_raw = sum(raw_scores.values()) + 1e-9
        composite_weights = {cid: rs / total_raw for cid, rs in raw_scores.items()}

        # ==========================================================
        # 步骤 4: 分层差异化鲁棒聚合 (Layer-differentiated Aggregation)
        # ==========================================================
        # 取样本架构以计算敏感度地图
        sample_weights = next(iter(client_data_map.values()))["weights"]
        layer_sensitivities = calculate_layer_sensitivity(sample_weights)
        inclusion_thresholds = calculate_inclusion_threshold(layer_sensitivities)
        
        valid_results = []
        aggregated_ndarrays = None

        for cid, data in client_data_map.items():
            cw = composite_weights[cid]
            fit_res = data["fit_res"]
            original_weights = data["weights"]
            tee_id = data["tee_id"]
            
            filtered_ndarrays = []
            dropped = 0
            
            # 按层（Layer by Layer）对矩阵块进行拦截与吸收
            for l_idx, layer in enumerate(original_weights):
                threshold_l = inclusion_thresholds[l_idx]
                if cw >= threshold_l:
                    # 你的模型综合权力达到了该层参数的修改要求 -> 放行，按你的权力吸收
                    filtered_ndarrays.append(layer * cw)
                else:
                    # 你的权力太低、或者本层过于深远重要 -> 无情丢弃该层所有贡献，置0阻塞该用户的该层传导
                    dropped += 1
                    filtered_ndarrays.append(np.zeros_like(layer))
                    
            # 加和进主全局累加器
            if aggregated_ndarrays is None:
                aggregated_ndarrays = list(filtered_ndarrays)
            else:
                aggregated_ndarrays = [a + b for a, b in zip(aggregated_ndarrays, filtered_ndarrays)]
            
            fit_res.parameters = ndarrays_to_parameters(filtered_ndarrays)
            valid_results.append((data["client_proxy"], fit_res))
            
            # 日志汇报：能清晰在后端看到谁的哪些深层参数更新被扣除了
            h_perf = self.trust_manager.history[cid]["ema_score"]
            status_icon = "✅" if cw > 1e-4 else "❌"
            
            client_logs.append(f"    🌟 [积分] 纯净贡献={data['s_content']:.3f} | 历史口碑={h_perf:.3f} | 统合话语权={cw:.3f}")
            if dropped > 0:
                client_logs.append(f"    📄 [Client {cid}] TEE: {tee_id[:8]}.. | {status_icon} 低于核心门限，已拦截 {dropped}/{len(original_weights)} 层高敏参数")
            else:
                client_logs.append(f"    📄 [Client {cid}] TEE: {tee_id[:8]}.. | {status_icon} 优质节点，通过全层聚合信任验证")

        self.audit_logger.log_batch(client_logs)
        self.contribution_validator.update_threshold_stats(round_positive_sims)
        self.audit_logger.log(f"🛡️  [TMAA Server] 圆满完成差异化聚合策略. 选定人数 ({len(valid_results)}).")

        # 将已完成聚合的矩阵块返回给系统执行下一轮全局广播
        if aggregated_ndarrays is not None:
            return ndarrays_to_parameters(aggregated_ndarrays), {}
        else:
            return super().aggregate_fit(server_round, valid_results, failures)
