import json
import math
import numpy as np
from typing import List, Tuple, Dict, Optional

import flwr as fl
from flwr.common import Parameters, FitRes, Scalar, ndarrays_to_parameters, parameters_to_ndarrays
from flwr.server.client_proxy import ClientProxy

from audit import AuditLogger

# === 导入从 strategy.py 单独拆分出去的子模块 ===
from trust_manager import TrustScoreManager
from contribution import ContributionValidator
from sensitivity import calculate_layer_sensitivities

# 为导入 Client 模块添加路径
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Client'))
try:
    from model import get_resnet18
except ImportError:
    pass

class TMAA_FedAvg(fl.server.strategy.FedAvg):
    """
    TMAA 增强版 FedAvg 策略：完全实现双流双层与动态门限
    引入了二次归一化、层级 L2-Norm Clipping、以及差分隐私数据的解析。
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
            m_attest, trust_score = self.trust_manager.evaluate_device_integrity(cid, report)
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
                "tee_id": report.get("header", {}).get("device_id", "Unknown")
            }
            
            # 计算基线参考真理 (参照物) 时，基于当前该人的 TrustScore 进行声量加权！
            if g_ref_weighted_sum is None:
                g_ref_weighted_sum = flat_update * trust_score
            else:
                g_ref_weighted_sum += flat_update * trust_score
            
            total_trust_score += trust_score
            
        self.audit_logger.log_batch(client_logs)
        client_logs.clear()

        if not client_data_map or total_trust_score == 0:
            self.audit_logger.log("    ❌ 本轮无有效客户端，中止。")
            return None, {}

        # ==========================================================
        # 步骤 2: 内容审查与实力分加权 (Content Scrutiny)
        # ==========================================================
        # 产生高信誉玩家主导的主基准梯度
        g_ref = g_ref_weighted_sum / total_trust_score
        
        # 理想情况下有一个 Root Dataset 算出的 g_root，此处仍以 g_ref 模拟
        g_root = g_ref
        
        all_s_contents = []
        round_positive_sims = []

        for cid, data in client_data_map.items():
            g_k = data["flat_update"]
            
            # 使用提取的 ContributionValidator 计算开根号映射后的实力分
            s_content, cos_root = self.contribution_validator.evaluate_content_score(g_k, g_ref, g_root)
            data["s_content"] = s_content
            
            if cos_root > 0:
                round_positive_sims.append(cos_root)
            all_s_contents.append(s_content)

        # ==========================================================
        # 步骤 3: 双流演进 —— History 更新 与 RawScore 生成
        # ==========================================================
        mu_avg = np.mean(all_s_contents) if all_s_contents else 0.0
        sigma_scale = np.std(all_s_contents) + 1e-6
        
        # 3.1 Stream A: 更新节点长期历史 (只关注客观 ContentScore)
        client_updates = {cid: d["s_content"] for cid, d in client_data_map.items()}
        self.trust_manager.update_history(client_updates, mu_avg, sigma_scale)
        
        # 3.2 Stream B: 综合计算绝对评分 RawScore (Trust, Content, History 连乘)
        for cid, data in client_data_map.items():
            data["raw_score"] = self.trust_manager.calculate_raw_score(
                cid, data["trust_score"], data["s_content"]
            )

        # ==========================================================
        # 步骤 4: 分层差异化鲁棒聚合与 L2-Norm裁剪
        # ==========================================================
        sample_weights = next(iter(client_data_map.values()))["weights"]
        
        # 基于逐层结构计算基准层权重 g_ref_layers
        g_ref_layers = []
        for i in range(len(sample_weights)):
            layer_sum = sum(data["weights"][i] * data["trust_score"] for data in client_data_map.values())
            g_ref_layers.append(layer_sum / total_trust_score)

        # 获取三维层级敏感度指纹与动态门槛
        layer_sensitivities = calculate_layer_sensitivities(client_data_map, g_ref_layers)
        
        valid_results = []
        aggregated_ndarrays = [np.zeros_like(layer) for layer in sample_weights]
        
        # 遍历每层对幸存者进行局部聚合
        for l_idx, layer_sens in enumerate(layer_sensitivities):
            threshold_l = layer_sens["inclusion_threshold"]
            clip_target = layer_sens["clip_target"]
            
            # 第一阶段过滤器：寻找能够越过这一层门槛的 VIP 玩家集合
            survivors = []
            for cid, data in client_data_map.items():
                if data["raw_score"] >= threshold_l:
                    survivors.append(cid)
            
            if not survivors:
                continue
                
            # 第二次归一化：重算该层剩余幸存者的权重和，以防分母缺失导致的步长衰减
            sum_raw_survivors = sum(client_data_map[cid]["raw_score"] for cid in survivors) + 1e-9
            
            for cid in survivors:
                data = client_data_map[cid]
                # 重新计算在这一层该人的分量
                normalized_weight_l = data["raw_score"] / sum_raw_survivors
                
                layer_grad = data["weights"][l_idx]
                norm_layer = np.linalg.norm(layer_grad)
                
                # 动态 L2-Norm 裁剪机制：若该层极其关键 (敏感分极高导致 clip target 很低)，重手一刀剪切！
                scale = max(1.0, norm_layer / clip_target)
                clipped_grad = layer_grad / scale
                
                aggregated_ndarrays[l_idx] += clipped_grad * normalized_weight_l

        # 生成日志
        for cid, data in client_data_map.items():
            fit_res = data["fit_res"]
            fit_res.parameters = ndarrays_to_parameters(data["weights"])
            valid_results.append((data["client_proxy"], fit_res))
            
            h_perf = self.trust_manager.fetch_history(cid)
            client_logs.append(f"    🌟 [积分] 纯净贡献={data['s_content']:.3f} | 历史口碑={h_perf:.3f} | 综合绝对权力={data['raw_score']:.3f}")

        # 将已经手工合并的结果赋值
        self.audit_logger.log_batch(client_logs)
        self.contribution_validator.update_threshold_stats(round_positive_sims)
        self.audit_logger.log(f"🛡️  [TMAA Server] 圆满完成层级二次归一化与动态截断聚合. 选定人数 ({len(valid_results)}).")

        return ndarrays_to_parameters(aggregated_ndarrays), {}

