# client/tmaa/inspector.py (隐私数据审计)
import torch
import numpy as np
from collections import Counter
import hashlib


class DataInspector:
    """
    TMAA 数据审计员
    负责在本地计算隐私保护的标量指标 (L3)
    """

    @staticmethod
    def audit_privacy_safe_metrics(dataloader):
        """
        对 DataLoader 进行零知识扫描
        返回: 标量指标字典
        """
        print("🛡️ [TMAA] 正在进行本地数据隐私审计...")

        all_labels = []
        all_img_hashes = []

        # 1. 快速扫描数据 (Metadata Scan)
        # 注意：这里我们遍历一次数据，但不存储原始图片
        for images, labels in dataloader:
            # 收集标签用于计算分布
            all_labels.extend(labels.tolist())

            # 收集图像哈希用于计算唯一性 (简单的感知哈希模拟)
            # 将 Tensor 转为 numpy 并计算简单的 MD5
            # 真实场景可以使用 pHash
            for img in images:
                img_bytes = img.cpu().numpy().tobytes()
                img_hash = hashlib.md5(img_bytes).hexdigest()
                all_img_hashes.append(img_hash)

        total_samples = len(all_labels)
        if total_samples == 0:
            return {"error": "Empty dataset"}

        # --- Metric 1: 信息熵 (Shannon Entropy) ---
        # 检测 Non-IID
        label_counts = Counter(all_labels)
        probs = np.array(list(label_counts.values())) / total_samples
        entropy = -np.sum(probs * np.log2(probs + 1e-9))

        # --- Metric 2: 唯一性比例 (Uniqueness Ratio) ---
        # 检测懒惰复制 / 女巫攻击
        unique_hashes = set(all_img_hashes)
        uniqueness_ratio = len(unique_hashes) / total_samples

        # --- Metric 3: 数据平衡性 (Data Balance Score) ---
        # 归一化熵值 (除以最大可能的熵 log2(10))
        max_entropy = np.log2(10)  # CIFAR-10 有 10 类
        balance_score = entropy / max_entropy

        metrics = {
            "sample_count": total_samples,
            "entropy_score": round(entropy, 4),
            "balance_score": round(balance_score, 4),  # 0~1, 越高越均衡
            "uniqueness_ratio": round(uniqueness_ratio, 4),  # 0~1, 越高越真实
            # 如果有条件做聚类分析，可以在这里添加 separability_score
        }

        print(f"🛡️ [TMAA] 审计完成: Entropy={metrics['entropy_score']}, Uniqueness={metrics['uniqueness_ratio']}")
        return metrics

    @staticmethod
    def calculate_initial_loss(net, dataloader, device):
        """
        计算初始适应损失 (L4 Anti-Flipping)
        """
        criterion = torch.nn.CrossEntropyLoss()
        total_loss = 0.0
        batches = 0

        net.eval()
        with torch.no_grad():
            for images, labels in dataloader:
                if batches > 5: break  # 只抽样前几个 Batch，节省时间
                images, labels = images.to(device), labels.to(device)
                outputs = net(images)
                loss = criterion(outputs, labels)
                total_loss += loss.item()
                batches += 1

        return total_loss / (batches + 1e-9)