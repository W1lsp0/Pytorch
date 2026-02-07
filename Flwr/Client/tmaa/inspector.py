"""
==============================================================================
🕵️ DataInspector 零知识隐私数据审计模块
==============================================================================
本模块实现各种数据隐私与安全检测算法，核心思想是"零知识审计"。
即在不查看原始数据内容(Pixel-Level)的前提下，通过统计学特征
发现潜在的恶意攻击行为。

监控维度:
    1. Information Entropy (信息熵) -> 检测 Non-IID 分布
    2. Cluster Separability (聚类分离度) -> 检测后门/投毒
    3. Uniqueness Ratio (唯一性比例) -> 检测懒惰复制/重复数据
    4. Initial Adaptation Loss (初始适应损失) -> 检测标签翻转

作者: Flwr 联邦学习项目
==============================================================================
"""

import numpy as np
import torch
import torch.nn as nn
from collections import Counter
import hashlib
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from typing import List, Dict, Any, Tuple
import sys

# ==================== 解决 Windows 中文乱码问题 ====================
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
# ================================================================

# ==================== 核心检测算法 ====================

def calc_entropy_score(labels: List[int]) -> float:
    """
    1. 信息熵 (Shannon Entropy) —— 检测 Non-IID 程度
    
    量化标签分布的"混乱程度"或"均衡程度"。
    
    Args:
        labels: 标签列表
        
    Returns:
        float: 归一化得分 (0.0 ~ 1.0)
            - 1.0: 绝对均衡 (IID)
            - 0.0: 只有单一类别 (极度 Non-IID)
            
    Math:
        H(X) = -∑ p(x) * log2(p(x))
        Score = H(X) / log2(N_classes)
    """
    if not labels:
        return 0.0
        
    counts = Counter(labels)
    total = len(labels)
    probs = np.array([count / total for count in counts.values()])
    
    # 计算香农熵
    entropy = -np.sum(probs * np.log2(probs + 1e-9))
    
    # 归一化 (CIFAR-10 有 10 类，最大熵为 log2(10))
    max_entropy = np.log2(10) 
    normalized_score = entropy / max_entropy
    return float(normalized_score)


def calc_backdoor_indicator(net: nn.Module, 
                           images: torch.Tensor, 
                           labels: torch.Tensor, 
                           target_class: int = 0) -> float:
    """
    2. 聚类分离度 (Cluster Separability) —— 检测后门/投毒
    
    检测某一类数据内部特征空间是否"分裂"成了两拨（一拨正常，一拨带触发器）。
    利用模型提取特征，对特定类别进行 K-Means(k=2) 聚类，计算轮廓系数。
    
    Args:
        net: 用于提取特征的模型
        images: 图像数据 (Batch)
        labels: 标签数据
        target_class: 怀疑的目标类别
        
    Returns:
        float: 轮廓系数 (-1.0 ~ 1.0)
            - > 0.6: 表示双峰分布显著(极可能存在后门)
            - < 0.3: 表示分布相对均匀(正常)
    """
    # 1. 提取特征 (Feature Extraction)
    # 简易实现：使用模型的输出 Logits 作为特征
    # 注意: 理想情况应Hook模型的 AvgPool 层获取 Embedding
    net.eval()
    with torch.no_grad():
        try:
            # 尝试获取特征层 (针对 ResNet 等标准结构)
            if hasattr(net, 'avgpool'):
                # 需要 forward hook 或修改 forward，这里为简化稳健性，直接用全模型输出
                # 在 ResNet-18 上，Logits 层之前的特征通常也具有可分性
                features = net(images)
            else:
                features = net(images)
        except:
            features = net(images)
            
        features = features.cpu().numpy()
        labels_np = labels.cpu().numpy()

    # 2. 只分析特定类别的数据
    indices = [i for i, x in enumerate(labels_np) if x == target_class]
    if len(indices) < 10: 
        return 0.0 # 样本太少，无法聚类
    
    target_features = features[indices]
    
    # 3. 尝试强制二分聚类 (K-Means k=2)
    # 假设：如果是后门攻击，带触发器的样本和正常样本在特征空间应有显著差异
    try:
        kmeans = KMeans(n_clusters=2, random_state=42, n_init=10).fit(target_features)
        cluster_labels = kmeans.labels_
        
        # 4. 计算轮廓系数 (Silhouette Coefficient)
        # 范围 [-1, 1]，分数越高表示聚类效果越好（即两拨数据分得越开）
        score = silhouette_score(target_features, cluster_labels)
    except Exception as e:
        # print(f"Cluster warning: {e}")
        score = 0.0
        
    return float(score)


def calc_uniqueness(images: torch.Tensor) -> float:
    """
    3. 唯一性比例 (Uniqueness Ratio) —— 检测懒惰复制
    
    检测是否存在大量完全重复的图片 (简单的复制粘贴)。
    使用 MD5 哈希进行快速比对。
    
    Args:
        images: 图像 Tensor
        
    Returns:
        float: 唯一样本比例 (0.0 ~ 1.0)
            - 1.0: 所有图片均不同
            - <0.1: 绝大部分是重复图片(懒惰节点)
    """
    hashes = []
    for img in images:
        # 将 tensor 转为 bytes 进行哈希
        img_bytes = img.cpu().numpy().tobytes()
        img_hash = hashlib.md5(img_bytes).hexdigest()
        hashes.append(img_hash)
        
    if not hashes:
        return 0.0
        
    unique_count = len(set(hashes))
    total_count = len(hashes)
    
    return unique_count / total_count


def calc_initial_loss(net: nn.Module, 
                     dataloader: torch.utils.data.DataLoader, 
                     device: torch.device) -> float:
    """
    4. 初始适应损失 (Initial Adaptation Loss) —— 检测标签翻转
    
    利用 Global Model 的"共同知识"检测"瞎标数据"。
    如果本地数据标签是乱标的(Flip)，即便是未训练的全局模型，Loss 也会异常偏高。
    
    Meaning:
        - Loss 适中: 数据分布与全局模型认知虽有差异但合理 (Non-IID)
        - Loss 极高: 标签可能被翻转或完全错误 (Label Flip)
        
    Returns:
        float: 平均 Loss 值
    """
    criterion = nn.CrossEntropyLoss()
    total_loss = 0.0
    count = 0
    
    net.eval()
    with torch.no_grad():
        for i, (images, labels) in enumerate(dataloader):
            images, labels = images.to(device), labels.to(device)
            outputs = net(images)
            loss = criterion(outputs, labels)
            total_loss += loss.item()
            count += 1
            # 仅抽样前 5 个 Batch，快速估算，避免全量计算
            if i >= 4: break 
            
    if count == 0:
        return 0.0
        
    return total_loss / count


class DataInspector:
    """
    TMAA 数据审计组件
    集成上述算法，提供统一的 .inspect() 接口
    """
    def __init__(self, device):
        self.device = device
        
    def inspect(self, net, dataloader) -> Dict[str, Any]:
        """
        执行全量多维审计
        
        Args:
            net: 待审计模型
            dataloader: 本地数据加载器
            
        Returns:
            Dict: 包含各项审计指标的字典
        """
        print("    🔍 [Inspector] 正在执行深度数据审计 (Deep Inspection)...")
        
        # 收集样本用于计算 (Entropy, Uniqueness, Clustering 需要一定量的数据)
        all_labels = []
        sample_images = [] 
        
        # 抽样参数 (最大 500 张图片用于分析，平衡速度与准确性)
        max_samples = 500
        current_samples = 0
        
        for images, labels in dataloader:
            all_labels.extend(labels.tolist())
            
            if current_samples < max_samples:
                # 收集样本 Tensor
                remaining = max_samples - current_samples
                batch_imgs = images[:remaining]
                sample_images.append(batch_imgs)
                current_samples += batch_imgs.shape[0]
            
            # 如果只需要计算 Entropy 可以在这里继续，否则可以 break
            # 为了获取全量 Entropy，我们遍历完 labels (开销很小)
        
        # 1. Non-IID (Entropy)
        entropy_score = calc_entropy_score(all_labels)
        
        # 2. Uniqueness
        if sample_images:
            stacked_images = torch.cat(sample_images, dim=0)
            uniqueness_score = calc_uniqueness(stacked_images)
        else:
            uniqueness_score = 0.0
            stacked_images = None
            
        # 3. Initial Loss
        init_loss = calc_initial_loss(net, dataloader, self.device)
        
        # 4. Backdoor Indicator (针对样本最多的 Top 3 类别)
        # 我们只检查主要类别，看是否在特征空间有明显分裂
        max_backdoor_score = 0.0
        suspected_class = -1
        
        if stacked_images is not None:
            sample_labels_tensor = torch.tensor(all_labels[:len(stacked_images)])
            
            # 统计样本最多的 Top 3 类别
            top_classes = [c for c, _ in Counter(all_labels).most_common(3)]
            
            for cls_id in top_classes:
                score = calc_backdoor_indicator(
                    net, stacked_images.to(self.device), 
                    sample_labels_tensor.to(self.device), 
                    target_class=cls_id
                )
                if score > max_backdoor_score:
                    max_backdoor_score = score
                    suspected_class = cls_id
        
        report = {
            "non_iid_entropy": round(entropy_score, 4),
            "uniqueness_ratio": round(uniqueness_score, 4),
            "initial_loss": round(init_loss, 4),
            "backdoor_score": round(max_backdoor_score, 4),
            "suspected_backdoor_class": suspected_class
        }
        
        self._print_report(report)
        return report

    def _print_report(self, report: dict):
        """美化打印审计报告"""
        print(f"    ┌{'─'*52}┐")
        print(f"    │  📊 审计结果摘要{' '*35}│")
        print(f"    ├{'─'*52}┤")
        print(f"    │  • 熵值 (Non-IID):      {report['non_iid_entropy']:.4f} (1.0=IID){' '*11}│")
        print(f"    │  • 唯一性 (Uniqueness): {report['uniqueness_ratio']:.4f} (1.0=Unique){' '*8}│")
        print(f"    │  • 初始损失 (Loss):     {report['initial_loss']:.4f}{' '*23}│")
        print(f"    │  • 后门聚类分数:        {report['backdoor_score']:.4f}{' '*23}│")
        if report['suspected_backdoor_class'] != -1:
            print(f"    │    ⚠️ 疑似后门类别:     Class {report['suspected_backdoor_class']}{' '*24}│")
        print(f"    └{'─'*52}┘")