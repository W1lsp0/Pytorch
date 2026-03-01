import math
import numpy as np
from collections import deque
from typing import List, Tuple

class ContributionValidator:
    """
    TMAA 核心检测器：计算梯度的一致性和贡献度，生成纯净的 ContentScore
    """
    def __init__(self, window_size: int = 5):
        self.sim_history = deque(maxlen=window_size)
        
    def evaluate_content_score(self, g_k: np.ndarray, g_ref: np.ndarray, g_root: np.ndarray) -> Tuple[float, float]:
        """
        计算 Phase 3 第 1 步的绝对实力分 (ContentScore)
        包含第一级非线性映射（开根号激励）与融合。
        """
        norm_k = np.linalg.norm(g_k) + 1e-9
        norm_ref = np.linalg.norm(g_ref) + 1e-9
        norm_root = np.linalg.norm(g_root) + 1e-9
        
        # 1. 一致性评测：与高信誉玩家主导的基准方向之间的夹角 (S_consist)
        cos_sim_ref = np.dot(g_k, g_ref) / (norm_k * norm_ref)
        s_consist = math.sqrt(max(0.0, float(cos_sim_ref)))
        
        # 2. 贡献度评测：与黄金标准数据集推导出的真理方向的夹角 (S_contrib)
        cos_sim_root = np.dot(g_k, g_root) / (norm_k * norm_root)
        s_contrib = math.sqrt(max(0.0, float(cos_sim_root)))
        
        # 3. 生成不含历史偏见的纯净内容分 (S_content)
        s_content = math.sqrt(s_consist * s_contrib)
        
        return s_content, float(cos_sim_root)

    def update_threshold_stats(self, positive_sims: List[float]):
        """更新历史共识统计信息，可用于未来 Adaptive Thresholding"""
        if not positive_sims: return
        self.sim_history.append(np.mean(positive_sims))
