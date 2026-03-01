import math
import numpy as np
from typing import List, Dict

def calculate_layer_sensitivities(client_data_map: dict, g_ref_layers: list) -> List[dict]:
    """
    计算模型每一层的三维敏感度指纹 (Tri-Dimensional Sensitivity Fingerprint)
    包含 Privacy (静态位置), Utility (动态梯度范数), Security (信任加权一致性)。
    
    返回: 各层敏感度与相关门控参数字典的列表
    """
    total_layers = len(g_ref_layers)
    if total_layers == 0:
        return []
        
    sensitivities = []
    
    # 预先计算 Utility: 全局参考梯度的各层 L2 范数
    ref_layer_norms = [np.linalg.norm(layer) for layer in g_ref_layers]
    max_ref_norm = max(ref_layer_norms) if max(ref_layer_norms) > 0 else 1.0

    # 预先提取信任分之和 (用于计算 Security 维度的加权散度)
    total_trust = sum(data["trust_score"] for data in client_data_map.values())
    total_trust = total_trust if total_trust > 0 else 1.0

    for l_idx in range(total_layers):
        # 1. 静态拓扑敏感度 (Privacy Risk) -> 越靠前越敏感 (指数衰减)
        tau_privacy = 3.0
        s_privacy = math.exp(-tau_privacy * (l_idx / total_layers))

        # 2. 动态效用敏感度 (Utility Disruption) -> 范数越大越关键
        s_utility = ref_layer_norms[l_idx] / max_ref_norm

        # 3. 对抗安全敏感度 (Adversarial Divergence) -> 层间发散度
        # 衡量大家在这一层上的共识度
        weighted_cos_sum = 0.0
        ref_layer = g_ref_layers[l_idx]
        norm_ref_l = ref_layer_norms[l_idx] + 1e-9
        
        for data in client_data_map.values():
            g_k_layer = data["weights"][l_idx]
            t_score = data["trust_score"]
            norm_k_l = np.linalg.norm(g_k_layer) + 1e-9
            cos_sim_l = np.dot(g_k_layer.flatten(), ref_layer.flatten()) / (norm_k_l * norm_ref_l)
            weighted_cos_sum += t_score * cos_sim_l
            
        s_security = 1.0 - (weighted_cos_sum / total_trust)
        # 限制在 [0, 1] 间
        s_security = max(0.0, min(1.0, float(s_security)))

        # 融合三维得分
        alpha, beta, gamma = 0.3, 0.4, 0.3
        s_raw_l = alpha * s_privacy + beta * s_utility + gamma * s_security
        
        # 计算该层的门限和裁剪控制
        mu_base = 0.3
        lambda_coef = 0.5
        tau_threshold = mu_base + lambda_coef * s_raw_l
        
        c_base = 2.0
        # 如果高度敏感，裁剪得越厉害
        clip_target = c_base / (s_raw_l + 0.01)

        sensitivities.append({
            "s_privacy": s_privacy,
            "s_utility": s_utility,
            "s_security": s_security,
            "s_total": s_raw_l,
            "inclusion_threshold": tau_threshold,
            "clip_target": clip_target
        })

    return sensitivities
