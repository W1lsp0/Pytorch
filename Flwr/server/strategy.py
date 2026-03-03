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
        # 记录上一轮的全局模型绝对权重，用于计算各节点的真实更新量 (ΔW)
        self.global_weights_old: Optional[List[np.ndarray]] = None

    def initialize_parameters(
        self, client_manager: fl.server.client_manager.ClientManager
    ) -> Optional[Parameters]:
        """
        初始化全局模型参数。
        因为我们需要截获每一次更新前的绝对权重以求取 Delta W，因此必须在开局时
        在此获得一份与 Client 端一致的初始模型镜像，并存入 self.global_weights_old。
        """
        # 尝试调用基类的方法 (如果配置了 initial_parameters)
        initial_parameters = super().initialize_parameters(client_manager)
        
        # 如果用户没有在 server.py 提供 initial_parameters，我们主动从 Client 仓库的主模型拿一份
        if initial_parameters is None:
            self.audit_logger.log("🛡️  [TMAA Server] 主动获取初始全局模型权重 (ResNet-18) 用于 Delta W 计算...")
            try:
                import torch
                from model import get_resnet18
                net = get_resnet18()
                weights = [val.cpu().numpy() for _, val in net.state_dict().items()]
                self.global_weights_old = weights
                initial_parameters = ndarrays_to_parameters(weights)
                
                # 构建可训练参数掩码 (用于后续剔除 BatchNorm 的 running_mean 和 running_var)
                mask_list = []
                for k, v in net.state_dict().items():
                    is_trainable = "running" not in k and "num_batches" not in k
                    mask_list.append(np.full(v.numel(), is_trainable, dtype=bool))
                self.trainable_mask = np.concatenate(mask_list)
                
            except Exception as e:
                self.audit_logger.log(f"    ❌ 获取初始模型失败: {e}，将回退到第一轮由某个 Client 上报。")
                self.trainable_mask = None
        else:
            self.global_weights_old = parameters_to_ndarrays(initial_parameters)
            # 注意: 如果提供了 initial_parameters，此处可能无法生成 mask，需依赖模型结构
            self.trainable_mask = None

        return initial_parameters

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
            
            # 提前提取真实的客户端 ID 用于日志显示，如果是异常格式则降级使用 cid 截断
            real_client_id = str(cid)[:5]
            if hasattr(fit_res, "metrics") and isinstance(fit_res.metrics, dict):
                real_client_id = fit_res.metrics.get("real_client_id", real_client_id)

            # ---- 阶段 0：黑名单绝对屏障拦截 ----
            if cid in self.trust_manager.blacklist:
                rejected_count += 1
                client_logs.append(f"    ⛔ [Client {real_client_id}] 黑名单拦截: 该节点已被系统永久清退")
                continue

            # ---- 解析安全报告 ----
            report = {}
            if "trust_report_json" in fit_res.metrics:
                try:
                    payload = json.loads(fit_res.metrics["trust_report_json"])
                    report = payload.get("trust_report", payload)
                except Exception as e:
                    client_logs.append(f"    ⚠️ [Client {real_client_id}] 报告解析失败: {e}")

            if not report:
                rejected_count += 1
                client_logs.append(f"    ❌ [Client {real_client_id}] 未提供可信报告，直接拦截")
                continue

            # ---- 硬门禁 + 指数衰减惩罚 → TrustScore ----
            m_attest, trust_score = self.trust_manager.evaluate_device_integrity(
                cid, report
            )
            if trust_score <= 0.0:
                rejected_count += 1
                client_logs.append(f"    ❌ [Client {real_client_id}] 信任评估未通过，熔断拦截")
                continue

            # ---- 提取客户端模型参数 ----
            try:
                # client_weights 提取的是本轮客户端经过 SGD 训练后的完整新模型 (W_new)
                client_weights = parameters_to_ndarrays(fit_res.parameters)
                
                # 如果服务端有上一轮的全局模型 W_old，则计算出客户端真实的更新量: ΔW = W_new - W_old
                if self.global_weights_old is not None:
                    # 将 ΔW 作为真正的特征图参与后续的 TMAA 余弦相似度计算与裁剪
                    weights = [w_new - w_old for w_new, w_old in zip(client_weights, self.global_weights_old)]
                else:
                    # 在第一轮还没有全局历史模型时，无奈退化为直接使用 W (或者全 0 的 ΔW)
                    weights = client_weights
                    
                flat_update = np.concatenate([w.flatten() for w in weights])
                
                # ---- 剔除 BatchNorm 统计量 (关键修复) ----
                # torchvision ResNet-18 的 state_dict 包含 running_mean/var 导致非训练参数的漂移掩盖了真实梯度
                # 借助预先计算的训练参数掩码 (self.trainable_mask) 进行过滤
                if hasattr(self, 'trainable_mask') and self.trainable_mask is not None:
                    flat_update = flat_update[self.trainable_mask]

            except Exception as e:
                rejected_count += 1
                client_logs.append(f"    ❌ [Client {real_client_id}] 参数解析失败: {e}")
                continue

            # 保存存活客户端的完整数据
            client_data_map[cid] = {
                "client_proxy": client,
                "fit_res": fit_res,
                "flat_update": flat_update,
                "weights": weights,
                "report": report,
                "real_client_id": real_client_id,
                "trust_score": trust_score,
                "tee_id": report.get("header", {}).get("device_id", "Unknown"),
            }

            # ---- 累加综合信任加权梯度（用于计算参考方向） ----
            # 注意：仅用 TrustScore (设备健康) 是不够的，内鬼的设备也是健康的。
            # 必须结合 Historical Performance (历史贡献信誉) 共同加权，防止内鬼夺权
            # 使用指数激化 (X^3) 使得低于 0.5 的劣迹节点权重迅速归零，杜绝其缓慢毒化 g_root
            h_perf = self.trust_manager.fetch_history(cid)
            compound_weight = trust_score * (h_perf ** 3)
            
            if g_ref_weighted_sum is None:
                g_ref_weighted_sum = flat_update * compound_weight
            else:
                g_ref_weighted_sum += flat_update * compound_weight

            total_trust_score += compound_weight

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

        # 批量进行成对参数比较、贡献度计算与调和融合
        batch_results = self.contribution_validator.evaluate_batch_content_scores(client_data_map, g_root)

        for cid, score_dict in batch_results.items():
            # 存入每个客户端的数据图
            client_data_map[cid]["s_content"] = score_dict["s_content"]
            client_data_map[cid]["s_contrib"] = score_dict["s_contrib"]
            client_data_map[cid]["s_consist"] = score_dict["s_consist"]
            
            cos_root = score_dict["cos_root"]
            if cos_root > 0:
                round_positive_sims.append(cos_root)
            all_s_contents.append(score_dict["s_content"])

        # ==================================================================
        # 阶段 3：双流正交演进
        # ==================================================================
        mu_avg = float(np.mean(all_s_contents)) if all_s_contents else 0.0
        sigma_scale = float(np.std(all_s_contents)) + 1e-6

        # ---- Stream B: 计算综合绝对评分 RawScore (使用旧资历 t-1) ----
        for cid, data in client_data_map.items():
            data["raw_score"] = self.trust_manager.calculate_raw_score(
                cid, data["trust_score"], data["s_content"]
            )

        # ---- Stream A: 更新历史信誉（仅基于纯净 ContentScore，生成新历史 t） ----
        content_scores = {cid: d["s_content"] for cid, d in client_data_map.items()}
        self.trust_manager.update_history(content_scores, mu_avg, sigma_scale)

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

        # 初始化全局聚合累加器（全零，强制浮点型以避免累加时类型转换失败）
        aggregated_ndarrays = [np.zeros_like(layer, dtype=np.float64) for layer in sample_weights]
        
        # 统计审计信息：记录每个客户端的逐层被采纳情况
        # 结构: cid -> { "included": 0, "excluded": 0, "avg_clip_scale": 0.0 }
        client_layer_stats = {cid: {"included": 0, "excluded": 0, "sum_scale": 0.0} for cid in client_data_map}

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

            # 统计 Excluded
            for cid in client_data_map:
                if cid not in survivors:
                    client_layer_stats[cid]["excluded"] += 1

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
                
                # 统计 Included 和 裁剪严厉程度
                client_layer_stats[cid]["included"] += 1
                client_layer_stats[cid]["sum_scale"] += scale

                # 加权累加到全局聚合结果
                aggregated_ndarrays[l_idx] += clipped_grad * normalized_weight

        # 生成本轮逐层处理的审计面板日志
        audit_panel = [
            f"    ┌{'─'*65}┐",
            f"    │  🔍 本轮客户端逐层聚合审计面板 (Total Layers: {num_layers:02d})             │",
            f"    ├{'─'*65}┤",
            f"    │  [CID真实编号] | 采纳层数 | 被拒层数 | 平均裁剪力度(Scale) │"
        ]
        
        for cid, stats in client_layer_stats.items():
            inc = stats["included"]
            exc = stats["excluded"]
            # avg_scale = 1.0 意味着完全没被裁剪
            avg_scale = stats["sum_scale"] / inc if inc > 0 else 0.0
            
            # 提取 payload 里包含的真实客户端 ID
            real_id = client_data_map[cid].get("real_client_id", str(cid)[:5])
            short_cid = f"Client {real_id}"
            
            # 高亮显示被拒绝过的或者是被极为严重裁剪的 (考虑到预训练权重的范数放大，阈值放宽到 20.0 倍)
            # 修复: 只有当一轮中大部分层被拒绝，或者平均 Scale 裁剪极其严重时才打警告
            # 否则像 Client 10 这种正常 Non-IID 只是极少数特征层离群，不该被标记为 ⚠️
            is_warn = (exc > inc * 2) or (avg_scale > 20.0) 
            flag = "⚠️" if is_warn else "✅"
            
            audit_panel.append(
                f"    │  {flag} {short_cid:<11} | Inc: {inc:03d} | Exc: {exc:02d} | Scale: {avg_scale:6.2f}x{' '*6}│"
            )
            
        audit_panel.append(f"    └{'─'*65}┘")
        # 直接输出这块面板到日志
        self.audit_logger.log_batch(audit_panel)

        # ==================================================================
        # 日志汇总与结果返回
        # ==================================================================
        # 恢复原始数据类型
        aggregated_ndarrays = [
            arr.astype(orig.dtype) for arr, orig in zip(aggregated_ndarrays, sample_weights)
        ]

        valid_results = []
        for cid, data in client_data_map.items():
            fit_res = data["fit_res"]
            fit_res.parameters = ndarrays_to_parameters(data["weights"])
            valid_results.append((data["client_proxy"], fit_res))

            h_perf = self.trust_manager.fetch_history(cid)
            real_id = data.get("real_client_id", str(cid)[:5])
            client_logs.append(
                f"    🌟 [Client {real_id}] "
                f"S_contrib={data.get('s_contrib', 0.0):.3f} | S_consist={data.get('s_consist', 0.0):.3f} | "
                f"S_content={data['s_content']:.3f} | "
                f"Hist={h_perf:.3f} | "
                f"Raw={data['raw_score']:.4f}"
            )

        self.audit_logger.log_batch(client_logs)
        # 暂不需要在这一步处理历史统计记录
        # self.contribution_validator.update_threshold_stats(round_positive_sims)
        self.audit_logger.log(
            f"🛡️  [TMAA Server] 第 {server_round} 轮聚合完成 | "
            f"存活节点: {len(valid_results)} | 拦截: {rejected_count}"
        )

        # ==================================================================
        # 重建全局模型 W_new = W_old + ΔW_global
        # ==================================================================
        if self.global_weights_old is not None:
            new_global_weights = [
                old_w + delta_w 
                for old_w, delta_w in zip(self.global_weights_old, aggregated_ndarrays)
            ]
        else:
            # 第一轮时，提取出来的本来就是绝对权重，直接继承
            new_global_weights = aggregated_ndarrays
            
        # 保存这轮生成的全局模型供下一轮作减法参考使用
        self.global_weights_old = new_global_weights

        return ndarrays_to_parameters(new_global_weights), {}
