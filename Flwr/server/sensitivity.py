import numpy as np

def calculate_layer_sensitivity(ndarrays: list) -> list:
    """
    计算模型每一层的敏感度分数 (SensitivityScore^l)
    这里为了简单起见，利用参数本身的特征结合静态位置信息进行估计。
    返回: 各层的敏感度列表 [0.0 - 1.0]
    """
    total_layers = len(ndarrays)
    if total_layers == 0:
        return []
    sensitivity_scores = []
    layer_norms = [np.linalg.norm(layer) for layer in ndarrays]
    max_norm = max(layer_norms) if max(layer_norms) > 0 else 1.0
    
    for i, layer in enumerate(ndarrays):
        # 1. 动态部分 (Utility): 范数/最大范数
        dynamic_score = layer_norms[i] / max_norm
        # 2. 静态部分 (Privacy): 越靠前的浅薄提取层往往包含隐性信息，但在分类器的全链接层可能更关乎投毒 (取决于模型设计，这里示例越深位置分数越低)
        static_score = 1.0 - (i / total_layers)
        
        # 3. 融合 (例如 70% 看大小，30% 看位置)
        final_score = 0.7 * dynamic_score + 0.3 * static_score
        sensitivity_scores.append(final_score)
        
    return sensitivity_scores

def calculate_inclusion_threshold(layer_sensitivities: list, threshold_base=0.1, lambda_coef=0.4) -> list:
    """
    根据每层敏感度计算准入门槛 InclusionThreshold^l
    敏感度更高的层，其更新最低准入分数的要求也就越高。
    """
    return [threshold_base + lambda_coef * s for s in layer_sensitivities]
