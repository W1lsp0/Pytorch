"""
==============================================================================
🔬 LayerSensitivity — TMAA 层级敏感度分析模块
==============================================================================
职责：
    为模型的每一层计算「三维敏感度指纹」，并据此生成：
    1. 动态准入门槛 (Inclusion Threshold)  —— 决定哪些节点有权修改该层
    2. 梯度裁剪上限 (Clip Target)          —— 限制被允许的节点能修改多少

三维敏感度指纹：
    S_privacy  = exp(-τ · l/L)                          静态拓扑（隐私泄露风险）
    S_utility  = ||∇W_ref^l||₂ / max_norm               动态效用（模型收敛关键度）
    S_security = 1 - Σ(TrustScore_k · cos(g_k^l, g_ref^l)) / Σ TrustScore_k
                                                         对抗安全（后门/投毒发散度）

准入门槛与裁剪公式：
    τ^l = μ_base + λ · S_total^l
    Clip^l = C_base / (S_total^l + ε)

作者: Flwr 联邦学习项目
==============================================================================
"""

import math
import numpy as np
from typing import List, Dict


def calculate_layer_sensitivities(client_data_map: dict,
                                  g_ref_layers: list) -> List[Dict[str, float]]:
    """
    计算模型每一层的三维敏感度指纹及对应的门控参数。

    参数:
        client_data_map: 存活客户端数据字典
                         每个条目需包含 "weights"（逐层参数列表）和 "trust_score"
        g_ref_layers:    全局参考梯度的逐层列表（由信任加权求和得到）

    返回:
        各层敏感度字典的列表，每个字典包含：
        - s_privacy:           隐私泄露风险分 ∈ [0, 1]
        - s_utility:           效用关键度分 ∈ [0, 1]
        - s_security:          对抗安全分 ∈ [0, 1]
        - s_total:             综合敏感度分
        - inclusion_threshold: 该层的准入门槛
        - clip_target:         该层的梯度裁剪上限
    """
    total_layers = len(g_ref_layers)
    if total_layers == 0:
        return []

    sensitivities = []

    # ---- 预计算：全局参考梯度各层 L2 范数 ----
    ref_layer_norms = [float(np.linalg.norm(layer)) for layer in g_ref_layers]
    max_ref_norm = max(ref_layer_norms) if max(ref_layer_norms) > 0 else 1.0

    # ---- 预计算：所有存活客户端的信任分总和 ----
    total_trust = sum(data["trust_score"] for data in client_data_map.values())
    total_trust = max(total_trust, 1e-9)  # 防零除

    # ---- 超参数配置 ----
    tau_privacy = 3.0       # 隐私衰减速率（越大浅层敏感度越突出）
    weight_privacy = 0.3    # 隐私维度融合权重 α
    weight_utility = 0.4    # 效用维度融合权重 β
    weight_security = 0.3   # 安全维度融合权重 γ
    mu_base = 0.05          # 准入门槛基线（最低质量保障，降低以适应晚期衰减）
    lambda_coef = 0.15      # 敏感度对门槛的放大系数（平滑以避免层级误杀）
    c_base = 2.0            # 裁剪基线常数

    for l_idx in range(total_layers):

        # ============ 维度 1：静态拓扑敏感度（隐私风险） ============
        # 浅层保留更多原始输入信息，遭受 DLG 攻击还原概率更高
        # 公式: S_privacy = exp(-τ · l/L)，浅层≈1，深层≈0
        s_privacy = math.exp(-tau_privacy * (l_idx / total_layers))

        # ============ 维度 2：动态效用敏感度（收敛关键度） ============
        # 梯度范数越大，说明该层正在剧烈学习主任务，不可被扰动
        # 公式: S_utility = ||∇W_ref^l||₂ / max_norm
        s_utility = ref_layer_norms[l_idx] / max_ref_norm

        # ============ 维度 3：对抗安全敏感度（后门发散度） ============
        # 衡量所有高信誉节点在该层的方向共识度
        # 共识越低（散度越高）→ 该层越可能正遭受后门攻击
        weighted_cos_sum = 0.0
        ref_layer = g_ref_layers[l_idx]
        norm_ref_l = ref_layer_norms[l_idx] + 1e-9

        for data in client_data_map.values():
            g_k_layer = data["weights"][l_idx]
            t_score = data["trust_score"]
            norm_k_l = float(np.linalg.norm(g_k_layer)) + 1e-9
            cos_sim_l = float(
                np.dot(g_k_layer.flatten(), ref_layer.flatten()) / (norm_k_l * norm_ref_l)
            )
            weighted_cos_sum += t_score * cos_sim_l

        # 公式: S_security = 1 - 加权平均余弦相似度
        s_security = 1.0 - (weighted_cos_sum / total_trust)
        s_security = max(0.0, min(1.0, s_security))  # 钳位到 [0, 1]

        # ============ 三维线性融合 ============
        s_total = (
            weight_privacy * s_privacy +
            weight_utility * s_utility +
            weight_security * s_security
        )

        # ============ 生成门控参数 ============
        # 准入门槛: 敏感度越高 → 门槛越高 → 只有高分节点才有资格修改
        inclusion_threshold = mu_base + lambda_coef * s_total

        # 裁剪上限: 敏感度越高 → 裁剪越严 → 即使进入也只能小幅修改
        clip_target = c_base / (s_total + 0.01)

        sensitivities.append({
            "s_privacy": round(s_privacy, 4),
            "s_utility": round(s_utility, 4),
            "s_security": round(s_security, 4),
            "s_total": round(s_total, 4),
            "inclusion_threshold": round(inclusion_threshold, 4),
            "clip_target": round(clip_target, 4),
        })

    return sensitivities
