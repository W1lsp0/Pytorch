"""
==============================================================================
📊 ContributionValidator — TMAA 贡献度验证模块 (v3.x 升级版)
==============================================================================
职责：
    评估客户端梯度更新的「内容质量」，生成不含历史偏见的纯净 ContentScore。
    本版本实现了基于**参数级成对相似度 (Pairwise Consistency)** 的防合谋一致性检测，
    并引入了**效用主导的非对称调和融合 (Asymmetric Harmonic Fusion)**。

核心算法：
    1. 优先贡献度评测 (S_contrib): 
       客户端梯度与黄金标准梯度的余弦相似度，经 ReLU + 开根号映射。
       衡量对主任务的绝对推力。
       S_contrib = √(max(0, CosSim(g_k, g_root)))
       
    2. 信任加权的跨客户端一致性 (S_consist): 
       计算当前节点与其他所有节点的余弦相似度，用对方的 TrustScore 赋权求和。
       衡量在安全节点群体中的共识度，从数学上瓦解女巫攻击。
       Raw_Consist_k = [Σ_{j≠k} Trust_j · max(0, CosSim(g_k, g_j))] / Σ_{j≠k} Trust_j
       S_consist = √(Raw_Consist_k)

    3. 非对称调和融合 (Asymmetric Harmonic Fusion): 
       取代几何平均，主动向 S_contrib 倾斜（β=2），保护拥有稀有长尾数据
       但合群度偏低的诚实节点。
       ContentScore = [(1+β²) · S_consist · S_contrib] / [β² · S_consist + S_contrib]

作者: Flwr 联邦学习项目
==============================================================================
"""

import math
import numpy as np
from typing import List, Tuple, Dict


class ContributionValidator:
    """
    TMAA 贡献度验证器
    """

    def __init__(self):
        # 调和融合倾斜超参数：β = 2.0，意味着 S_contrib 的权重是 S_consist 的 4 倍
        self.beta_fusion = 2.0
        self.beta_sq = self.beta_fusion ** 2

    def evaluate_batch_content_scores(self, client_data_map: Dict[str, dict], g_root: np.ndarray) -> Dict[str, dict]:
        """
        批量评估所有存活客户端的纯净内容质量分。
        因为成对一致性检测需要全局视野（看到其他所有人的梯度和信任分），所以必须批量处理。

        参数:
            client_data_map: 存活客户端数据字典，结构为 {cid: {"flat_update": ndarray, "trust_score": float, ...}}
            g_root:          黄金标准梯度（由 Root Dataset 或加权共识推导）

        返回:
            更新后的客户端结果字典，key 为 cid，value 为包含分数的字典：
            { cid: {"s_content": float, "s_contrib": float, "s_consist": float, "cos_root": float} }
        """
        cids = list(client_data_map.keys())
        n_clients = len(cids)
        result_map = {}
        
        if n_clients == 0:
            return result_map

        # ------------------------------------------------------------------
        # 预计算：所有客户端梯度的 L2 范数及与 g_root 的余弦相似度
        # ------------------------------------------------------------------
        norm_root = float(np.linalg.norm(g_root)) + 1e-9
        
        norms = {}
        s_contrib_map = {}
        cos_root_map = {}
        
        for cid in cids:
            g_k = client_data_map[cid]["flat_update"]
            norm_k = float(np.linalg.norm(g_k)) + 1e-9
            norms[cid] = norm_k
            
            # 计算与黄金梯度的夹角
            # 采用仿射变换将 [-1, 1] 映射到 [0, 1]，防止极度 Non-IID (正交或微负) 直接被一刀切成 0
            cos_root = float(np.dot(g_k, g_root) / (norm_k * norm_root))
            print(f"[DEBUG SIM] CID: {cid[:5]} | norm_k: {norm_k:.4f} | norm_root: {norm_root:.4f} | cos_root: {cos_root:.6f}", flush=True)
            cos_root_map[cid] = cos_root
            shifted_cos = (cos_root + 1.0) / 2.0
            s_contrib_map[cid] = math.sqrt(max(0.0, shifted_cos))
            
        # 如果只有一个客户端，无法计算成对一致性，直接 fallback 为 S_contrib
        if n_clients == 1:
            cid = cids[0]
            s_c = s_contrib_map[cid]
            result_map[cid] = {
                "s_content": s_c,
                "s_contrib": s_c,
                "s_consist": 1.0,  # 唯一的节点绝对“合群”
                "cos_root": cos_root_map[cid]
            }
            return result_map

        # ------------------------------------------------------------------
        # Step 1: 构建参数级成对相似度矩阵并计算 Trust-Weighted Consistency
        # ------------------------------------------------------------------
        s_consist_map = {}
        
        for i_idx, cid_k in enumerate(cids):
            g_k = client_data_map[cid_k]["flat_update"]
            norm_k = norms[cid_k]
            
            weighted_sim_sum = 0.0
            trust_sum_others = 0.0
            
            # 和其他所有人比对
            for j_idx, cid_j in enumerate(cids):
                if i_idx == j_idx:
                    continue
                    
                g_j = client_data_map[cid_j]["flat_update"]
                norm_j = norms[cid_j]
                trust_j = client_data_map[cid_j]["trust_score"]
                
                # Pairwise Cosine Similarity
                sim_k_j = float(np.dot(g_k, g_j) / (norm_k * norm_j))
                
                # 采用仿射变换保证非极端对立的 Non-IID 客户端仍有基础分数支撑
                shifted_sim_k_j = (sim_k_j + 1.0) / 2.0
                weighted_sim_sum += trust_j * shifted_sim_k_j
                trust_sum_others += trust_j
                
            # 计算加权共识并进行根号映射
            if trust_sum_others > 0:
                raw_consist = weighted_sim_sum / trust_sum_others
            else:
                raw_consist = 0.0
                
            s_consist_map[cid_k] = math.sqrt(max(0.0, raw_consist))

        # ------------------------------------------------------------------
        # Step 2: 效用主导的非对称调和融合 (Asymmetric Harmonic Fusion)
        # ------------------------------------------------------------------
        for cid in cids:
            s_contrib = s_contrib_map[cid]
            s_consist = s_consist_map[cid]
            
            # ContentScore = [(1+β²) * consist * contrib] / [β² * consist + contrib + ε]
            numerator = (1.0 + self.beta_sq) * s_consist * s_contrib
            denominator = self.beta_sq * s_consist + s_contrib + 1e-9
            
            content_score = numerator / denominator
            
            # 安全钳位，以防万一
            content_score = max(0.0, min(1.0, content_score))
            
            result_map[cid] = {
                "s_content": content_score,
                "s_contrib": s_contrib,
                "s_consist": s_consist,
                "cos_root": cos_root_map[cid]
            }
            
        return result_map
