"""
==============================================================================
📊 ContributionValidator — TMAA 贡献度验证模块
==============================================================================
职责：
    评估客户端梯度更新的「内容质量」，生成不含历史偏见的纯净 ContentScore。

核心算法：
    1. 一致性评测 (S_consist): 与高信誉基准梯度的余弦相似度，经 ReLU + 开根号激励
    2. 贡献度评测 (S_contrib): 与黄金标准梯度的余弦相似度，经 ReLU + 开根号激励
    3. 几何融合: ContentScore = √(S_consist × S_contrib)

数学公式：
    S_contrib = √(ReLU(CosSim(g_k, g_root)))
    S_consist = √(ReLU(CosSim(g_k, g_ref)))
    ContentScore = √(S_contrib × S_consist)

作者: Flwr 联邦学习项目
==============================================================================
"""

import math
import numpy as np
from collections import deque
from typing import List, Tuple


class ContributionValidator:
    """
    TMAA 贡献度验证器
    基于余弦相似度和非线性映射，评估客户端梯度更新的方向对齐度和贡献价值。
    """

    def __init__(self, window_size: int = 5):
        """
        初始化验证器。

        参数:
            window_size: 滑动窗口大小，用于维护历史余弦相似度统计（自适应阈值用）
        """
        # 历史正向相似度的滑动窗口（用于未来的 Adaptive Thresholding）
        self.sim_history: deque = deque(maxlen=window_size)

    def evaluate_content_score(self, g_k: np.ndarray,
                               g_ref: np.ndarray,
                               g_root: np.ndarray) -> Tuple[float, float]:
        """
        计算客户端梯度的纯净内容质量分。

        两步非线性映射 + 几何平均融合：
            步骤 1: S_consist = √(max(0, CosSim(g_k, g_ref)))
                     衡量与高信誉共识方向的对齐度
            步骤 2: S_contrib = √(max(0, CosSim(g_k, g_root)))
                     衡量与黄金标准学习方向的对齐度
            步骤 3: ContentScore = √(S_consist × S_contrib)
                     几何平均，保持0.9×0.9=0.9的保值特性

        参数:
            g_k:    客户端梯度的扁平化向量
            g_ref:  信任加权的全局参考梯度（由高信誉节点主导）
            g_root: 黄金标准梯度（由 Root Dataset 或加权共识推导）

        返回:
            (content_score, cos_sim_root) 元组
            - content_score: 纯净内容实力分 ∈ [0, 1]
            - cos_sim_root:  与黄金标准的原始余弦相似度（用于统计）
        """
        # 预计算向量范数（+ε 防零除）
        norm_k = np.linalg.norm(g_k) + 1e-9
        norm_ref = np.linalg.norm(g_ref) + 1e-9
        norm_root = np.linalg.norm(g_root) + 1e-9

        # ---- 一致性评测：与高信誉基准方向的夹角 ----
        cos_sim_ref = float(np.dot(g_k, g_ref) / (norm_k * norm_ref))
        # ReLU 截断负相似度（反向更新视为零贡献）+ 开根号激励
        s_consist = math.sqrt(max(0.0, cos_sim_ref))

        # ---- 贡献度评测：与黄金标准方向的夹角 ----
        cos_sim_root = float(np.dot(g_k, g_root) / (norm_k * norm_root))
        s_contrib = math.sqrt(max(0.0, cos_sim_root))

        # ---- 几何平均融合：防止连乘衰减 ----
        # 例: 两者均为 0.9 → √(0.9×0.9) = 0.9（保值）
        # 任一为 0 → 结果为 0（安全性保留）
        content_score = math.sqrt(s_consist * s_contrib)

        return content_score, cos_sim_root

    def update_threshold_stats(self, positive_sims: List[float]) -> None:
        """
        更新历史正向相似度统计信息。

        用于未来实现自适应阈值（Adaptive Thresholding）：
        在极端 Non-IID 场景下，动态调整判定阈值，避免误杀偏科但诚实的节点。

        参数:
            positive_sims: 本轮所有正向余弦相似度值列表
        """
        if not positive_sims:
            return
        self.sim_history.append(float(np.mean(positive_sims)))
