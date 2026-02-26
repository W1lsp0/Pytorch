import numpy as np
from collections import deque
from typing import List

class ContributionValidator:
    """
    核心检测器：用于自适应动态调整与根数据集或者可信基准梯度的相似度历史门限
    """
    def __init__(self, window_size: int = 5):
        self.sim_history = deque(maxlen=window_size)
        
    def update_threshold_stats(self, positive_sims: List[float]):
        """
        更新历史共识统计信息，调整动态阈值
        """
        if not positive_sims: return
        self.sim_history.append(np.mean(positive_sims))
