
import numpy as np
import torch
import torch.nn as nn
from collections import Counter
import hashlib
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from typing import List, Dict, Any, Tuple

# =============================================================================
# 🕵️ DataInspector - 零知识隐私数据审计模块
# =============================================================================
# 核心思想：在不查看原始数据内容（Pixel-Level）的前提下，通过统计学特征由于
# 发现潜在的恶意攻击行为。
# 
# 监控维度：
# 1. Non-IID 程度 (香农熵)
# 2. 后门/投毒攻击 (聚类分离度)
# 3. 懒惰复制/重复数据 (唯一性比例)
# 4. 标签翻转 (初始适应损失)
# =============================================================================

def calc_entropy_score(labels: List[int]) -> float:
    """
    1. 信息熵 (Shannon Entropy) —— 检测 Non-IID
    
    量化标签分布的"混乱程度"。
    
    Args:
        labels: 标签列表
        
    Returns:
        float: 0.0 ~ 1.0, 1.0 代表绝对均衡，0.0 代表只有一类
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
    
    检测某一类数据内部是否"分裂"成了两拨（一拨正常，一拨带触发器）。
    利用模型提取特征，对特定类别进行 K-Means(k=2) 聚类，计算轮廓系数。
    
    Args:
        net: 用于提取特征的模型
        images: 图像数据 (Batch)
        labels: 标签数据
        target_class: 怀疑的目标类别
        
    Returns:
        float: 轮廓系数 (-1.0 ~ 1.0), >0.6 表示双峰分布显著(可能存在后门)
    """
    # 1. 提取特征 (Feature Extraction)
    # 简易实现：使用模型的倒数第二层输出
    # 这里我们假设 net 有 forward_features 方法，或者我们手动修改 forward
    # 如果没有，我们可以临时 hook 或者使用 avgpool 层的输出
    
    features_list = []
    
    # 简化：直接使用模型输出作为特征 (虽然效果不如 Feature Map，但在 ResNet 上勉强可用)
    # 更好的做法是 hook avgpool 层
    net.eval()
    with torch.no_grad():
        # 这里为了通用性，暂时用 output，理想情况应该用 embedding
        # 如果模型有 backbone 属性，可以用 net.backbone(images)
        try:
            # 尝试调用 features 之类的方法
            if hasattr(net, 'features'):
                output = net.features(images)
                output = nn.functional.adaptive_avg_pool2d(output, (1, 1))
                features = output.view(output.size(0), -1)
            # ResNet 通常有 avgpool
            elif hasattr(net, 'avgpool'):
                # 这需要配合 hook，比较复杂，这里简化处理：
                # 依然跑完整 forward，取 output (Logits)
                features = net(images)
            else:
                features = net(images)
        except:
            features = net(images)
            
        features = features.cpu().numpy()
        labels_np = labels.cpu().numpy()

    # 2. 只分析特定类别
    indices = [i for i, x in enumerate(labels_np) if x == target_class]
    if len(indices) < 10: 
        return 0.0 # 样本太少不算
    
    target_features = features[indices]
    
    # 3. 尝试强制二分聚类 (K-Means k=2)
    # 如果该类纯净，强行分两类效果会很差
    try:
        kmeans = KMeans(n_clusters=2, random_state=42, n_init=10).fit(target_features)
        cluster_labels = kmeans.labels_
        
        # 4. 计算轮廓系数 (0~1)
        # 如果分数很高，说明这一类数据内部确实存在两个截然不同的子群
        score = silhouette_score(target_features, cluster_labels)
    except Exception as e:
        print(f"Cluster warning: {e}")
        score = 0.0
        
    return float(score)


def calc_uniqueness(images: torch.Tensor) -> float:
    """
    3. 唯一性比例 (Uniqueness Ratio) —— 检测懒惰复制
    
    检测图片是否是简单的复制粘贴。
    
    Args:
        images: 图像 Tensor
        
    Returns:
        float: 唯一样本比例 (0.0 ~ 1.0)
    """
    hashes = []
    for img in images:
        # 将 tensor 转为 bytes 进行哈希
        img_bytes = img.cpu().numpy().tobytes()
        # MD5 速度极快
        img_hash = hashlib.md5(img_bytes).hexdigest()
        hashes.append(img_hash)
        
    if not hashes:
        return 0.0
        
    unique_count = len(set(hashes))
    total_count = len(hashes)
    
    return unique_count / total_count # 1.0 代表全都不一样


def calc_initial_loss(net: nn.Module, 
                     dataloader: torch.utils.data.DataLoader, 
                     device: torch.device) -> float:
    """
    4. 初始适应损失 (Initial Adaptation Loss) —— 检测标签翻转
    
    利用Global Model的"共同知识"检测"瞎标数据"。
    
    Args:
        net: 全局模型
        dataloader: 本地数据
        device: 运行设备
        
    Returns:
        float: 平均 Loss
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
            # 抽样前 5 个 Batch 即可，不需要跑全量，节省时间
            if i >= 4: break # 0..4 is 5 batches
            
    if count == 0:
        return 0.0
        
    return total_loss / count


class DataInspector:
    """
    TMAA 数据审计组件
    集成上述算法，提供统一接口
    """
    def __init__(self, device):
        self.device = device
        
    def inspect(self, net, dataloader) -> Dict[str, Any]:
        """执行全量审计"""
        print("    🔍 Inspector: Running deep inspection...")
        
        # 收集少量样本用于快速计算 (避免遍历整个 dataset 太慢)
        # 这里为了准确性，如果是轻量级算法(Entropy, MD5)可以跑全量或大样本
        # 如果是耗时算法(K-Means)，建议抽样
        
        all_labels = []
        sample_images = [] # 存一部分 image tensor 用于计算 uniqueness 和 backdoor
        
        # 抽样参数
        max_samples = 500
        current_samples = 0
        
        for images, labels in dataloader:
            all_labels.extend(labels.tolist())
            
            if current_samples < max_samples:
                # 收集样本
                remaining = max_samples - current_samples
                batch_imgs = images[:remaining]
                sample_images.append(batch_imgs)
                current_samples += batch_imgs.shape[0]
        
        # 1. Non-IID (Entropy)
        entropy_score = calc_entropy_score(all_labels)
        
        # 2. Uniqueness
        if sample_images:
            stacked_images = torch.cat(sample_images, dim=0)
            uniqueness_score = calc_uniqueness(stacked_images)
        else:
            uniqueness_score = 0.0
            
        # 3. Initial Loss
        init_loss = calc_initial_loss(net, dataloader, self.device)
        
        # 4. Backdoor Indicator (针对所有类别或 Top 3 样本最多的类别)
        # 简化版：我们只检查所有的类别，看哪个分数最高
        max_backdoor_score = 0.0
        suspected_class = -1
        
        if sample_images:
            # 仅在有样本时计算
            sample_labels_tensor = torch.tensor(all_labels[:len(stacked_images)])
            
            # 统计样本最多的 Top 3 类别进行检查，节省时间
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
        
        print(f"    🔍 Inspection Result: {report}")
        return report