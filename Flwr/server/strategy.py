"""
==============================================================================
🌐 TMAA_FedAvg — TMAA 增强版联邦平均聚合策略
==============================================================================
职责：
    作为联邦学习服务端的核心聚合引擎，串联以下四大防御阶段：

    阶段 1: 设备完整性评估（硬门禁 + 软感知 → TrustScore）
    阶段 2: 梯度贡献度审查（余弦对齐 + 非线性映射 → ContentScore）
    阶段 3: 双流正交演进（Stream A: HistPerf EMA 更新 / Stream B: RawScore 生成）
    阶段 4: 分层差异化鲁棒聚合（三维敏感度 + 二次归一化 + L2-Norm 动态裁剪）

核心公式：
    ContentScore = √(S_consist × S_contrib)
    RawScore = Trust^α × Content^β × Hist^γ
    ΔW_global^l = Σ_{k∈Φ^l} [ RawScore_k / Σ_{j∈Φ^l} RawScore_j ] × Clip(ΔW_k^l)

作者: Flwr 联邦学习项目
==============================================================================
"""

import json
import numpy as np
from typing import List, Tuple, Dict, Optional

import flwr as fl
from flwr.common import (
    Parameters, FitRes, Scalar,
    ndarrays_to_parameters, parameters_to_ndarrays,
)
from flwr.server.client_proxy import ClientProxy

from audit import AuditLogger
from trust_manager import TrustScoreManager
from contribution import ContributionValidator
from sensitivity import calculate_layer_sensitivities

# 添加 Client 模块路径（用于导入共享的模型定义）
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Client'))
try:
    from model import get_resnet18
except ImportError:
    pass


class TMAA_FedAvg(fl.server.strategy.FedAvg):
    """
    TMAA 增强版 FedAvg 策略

    与传统 FedAvg 的核心差异：
        - 放弃了「一刀切」的全局加权平均
        - 采用「逐层差异化控制 + 二次归一化 + 动态裁剪」的鲁棒聚合机制
        - 通过正交双流架构解耦「历史信誉更新」与「聚合权重计算」
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 初始化核心防御组件
        self.trust_manager = TrustScoreManager()           # 信任分管理器
        self.contribution_validator = ContributionValidator()  # 贡献度验证器
        self.audit_logger = AuditLogger()                  # 审计日志记录器

    def aggregate_fit(
        self,
        server_round: int,
        results: List[Tuple[ClientProxy, FitRes]],
        failures: List[str | BaseException],
    ) -> Tuple[Optional[Parameters], Dict[str, Scalar]]:
        """
        核心聚合入口：接收各客户端的训练结果，执行四阶段防御后返回聚合参数。

        参数:
            server_round: 当前联邦学习轮次
            results:      客户端训练结果列表 [(ClientProxy, FitRes), ...]
            failures:     失败的客户端列表

        返回:
            (聚合后的全局参数, 聚合指标字典)
        """
        self.audit_logger.log(
            f"\n🛡️  [TMAA Server] 第 {server_round} 轮 | 审计阶段开始..."
        )

        if not results:
            return None, {}

        # 存活客户端数据字典: { cid: {所有相关数据} }
        client_data_map: Dict[str, dict] = {}
        client_logs: List[str] = []
        rejected_count = 0

        # ==================================================================
        # 阶段 1：设备完整性评估与信任分计算
        # ==================================================================
        total_trust_score = 0.0
        g_ref_weighted_sum = None  # 信任加权梯度累加器

        for client, fit_res in results:
            cid = client.cid

            # ---- 解析安全报告 ----
            report = {}
            if "trust_report_json" in fit_res.metrics:
                try:
                    payload = json.loads(fit_res.metrics["trust_report_json"])
                    report = payload.get("trust_report", payload)
                except Exception as e:
                    client_logs.append(f"    ⚠️ [Client {cid}] 报告解析失败: {e}")

            if not report:
                rejected_count += 1
                client_logs.append(f"    ❌ [Client {cid}] 未提供可信报告，直接拦截")
                continue

            # ---- 硬门禁 + 指数衰减惩罚 → TrustScore ----
            m_attest, trust_score = self.trust_manager.evaluate_device_integrity(
                cid, report
            )
            if trust_score <= 0.0:
                rejected_count += 1
                client_logs.append(f"    ❌ [Client {cid}] 信任评估未通过，熔断拦截")
                continue

            # ---- 提取客户端模型参数 ----
            try:
                weights = parameters_to_ndarrays(fit_res.parameters)
                flat_update = np.concatenate([w.flatten() for w in weights])
            except Exception as e:
                rejected_count += 1
                client_logs.append(f"    ❌ [Client {cid}] 参数解析失败: {e}")
                continue

            # 保存存活客户端的完整数据
            client_data_map[cid] = {
                "client_proxy": client,
                "fit_res": fit_res,
                "flat_update": flat_update,
                "weights": weights,
                "report": report,
                "trust_score": trust_score,
                "tee_id": report.get("header", {}).get("device_id", "Unknown"),
            }

            # ---- 累加信任加权梯度（用于计算参考方向） ----
            if g_ref_weighted_sum is None:
                g_ref_weighted_sum = flat_update * trust_score
            else:
                g_ref_weighted_sum += flat_update * trust_score

            total_trust_score += trust_score

        # 批量输出第一阶段日志
        self.audit_logger.log_batch(client_logs)
        client_logs.clear()

        if not client_data_map or total_trust_score == 0:
            self.audit_logger.log("    ❌ 本轮无有效客户端，聚合中止。")
            return None, {}

        # ==================================================================
        # 阶段 2：梯度贡献度审查 → ContentScore
        # ==================================================================
        # 生成高信誉玩家主导的参考梯度方向
        g_ref = g_ref_weighted_sum / total_trust_score

        # 注: 理想情况下 g_root 应由服务端的 Root Dataset 独立计算
        # 此处以加权共识梯度作为替代
        g_root = g_ref

        all_s_contents: List[float] = []
        round_positive_sims: List[float] = []

        for cid, data in client_data_map.items():
            g_k = data["flat_update"]

            # 计算开根号映射后的纯净内容实力分
            s_content, cos_root = self.contribution_validator.evaluate_content_score(
                g_k, g_ref, g_root
            )
            data["s_content"] = s_content

            if cos_root > 0:
                round_positive_sims.append(cos_root)
            all_s_contents.append(s_content)

        # ==================================================================
        # 阶段 3：双流正交演进
        # ==================================================================
        mu_avg = float(np.mean(all_s_contents)) if all_s_contents else 0.0
        sigma_scale = float(np.std(all_s_contents)) + 1e-6

        # ---- Stream A: 更新历史信誉（仅基于纯净 ContentScore） ----
        content_scores = {cid: d["s_content"] for cid, d in client_data_map.items()}
        self.trust_manager.update_history(content_scores, mu_avg, sigma_scale)

        # ---- Stream B: 计算综合绝对评分 RawScore ----
        for cid, data in client_data_map.items():
            data["raw_score"] = self.trust_manager.calculate_raw_score(
                cid, data["trust_score"], data["s_content"]
            )

        # ==================================================================
        # 阶段 4：分层差异化鲁棒聚合
        # ==================================================================
        sample_weights = next(iter(client_data_map.values()))["weights"]
        num_layers = len(sample_weights)

        # ---- 计算逐层参考梯度（信任加权） ----
        g_ref_layers = []
        for i in range(num_layers):
            layer_sum = sum(
                data["weights"][i] * data["trust_score"]
                for data in client_data_map.values()
            )
            g_ref_layers.append(layer_sum / total_trust_score)

        # ---- 获取三维层级敏感度指纹 ----
        layer_sensitivities = calculate_layer_sensitivities(
            client_data_map, g_ref_layers
        )

        # 初始化全局聚合累加器（全零）
        aggregated_ndarrays = [np.zeros_like(layer) for layer in sample_weights]

        # ---- 逐层执行「门控过滤 + 二次归一化 + 动态裁剪」 ----
        for l_idx, layer_sens in enumerate(layer_sensitivities):
            threshold_l = layer_sens["inclusion_threshold"]
            clip_target = layer_sens["clip_target"]

            # 步骤 1: 筛选幸存者集合 Φ^l
            # 只有绝对分 RawScore ≥ 该层门槛的节点才有资格参与聚合
            survivors = [
                cid for cid, data in client_data_map.items()
                if data["raw_score"] >= threshold_l
            ]

            if not survivors:
                # 该层无人达标，保留全零（不更新）
                continue

            # 步骤 2: 二次归一化（解决分母缺失问题）
            # 被淘汰节点的权重不会凭空消失，幸存者自动填补，权重总和恢复为 1
            sum_raw_survivors = sum(
                client_data_map[cid]["raw_score"] for cid in survivors
            ) + 1e-9

            # 步骤 3: 对每个幸存者执行动态裁剪并加权累加
            for cid in survivors:
                data = client_data_map[cid]

                # 局部归一化权重
                normalized_weight = data["raw_score"] / sum_raw_survivors

                # 提取该层梯度
                layer_grad = data["weights"][l_idx]
                norm_layer = float(np.linalg.norm(layer_grad))

                # 动态 L2-Norm 裁剪
                # 敏感度越高 → clip_target 越小 → 裁剪越严格
                # 比喻: "进了核心机密室，但笔被换成了极细铅笔"
                scale = max(1.0, norm_layer / clip_target)
                clipped_grad = layer_grad / scale

                # 加权累加到全局聚合结果
                aggregated_ndarrays[l_idx] += clipped_grad * normalized_weight

        # ==================================================================
        # 日志汇总与结果返回
        # ==================================================================
        valid_results = []
        for cid, data in client_data_map.items():
            fit_res = data["fit_res"]
            fit_res.parameters = ndarrays_to_parameters(data["weights"])
            valid_results.append((data["client_proxy"], fit_res))

            h_perf = self.trust_manager.fetch_history(cid)
            client_logs.append(
                f"    🌟 [Client {cid}] "
                f"贡献={data['s_content']:.3f} | "
                f"信誉={h_perf:.3f} | "
                f"综合={data['raw_score']:.4f}"
            )

        self.audit_logger.log_batch(client_logs)
        self.contribution_validator.update_threshold_stats(round_positive_sims)
        self.audit_logger.log(
            f"🛡️  [TMAA Server] 第 {server_round} 轮聚合完成 | "
            f"存活节点: {len(valid_results)} | 拦截: {rejected_count}"
        )

        return ndarrays_to_parameters(aggregated_ndarrays), {}
