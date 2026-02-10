# -*- coding: utf-8 -*-
"""
==============================================================================
文件名: dataset.py
功能: 数据加载与预处理模块
描述:
    本模块负责加载 CIFAR-10 数据集，并为每个联邦学习客户端划分专属的数据分片。
    主要功能包括：
    1. 数据增强 (Data Augmentation): 随机裁剪、翻转等。
    2. 数据标准化 (Normalization): 将像素值归一化到标准范围。
    3. 数据分片 (Data Partitioning): 将训练集切分为多个子集供不同客户端使用。
    4. 投毒集成: 调用 PoisonedDataset 对特定客户端的数据进行投毒处理。

作者: Flwr 联邦学习项目组
日期: 2024
==============================================================================
"""

import torch
import torchvision
import torchvision.transforms as transforms
from torch.utils.data import DataLoader, Subset, random_split
from typing import Tuple, Optional, List
import numpy as np

# 从投毒模块导入包装器
from poison.attack_wrapper import PoisonedDataset

def load_data(
    client_id: int,
    total_clients: int,
    attack_type: Optional[str] = None,
    poison_rate: float = 0.0,
    target_label: int = 0
) -> Tuple[DataLoader, DataLoader]:
    """
    加载并划分 CIFAR-10 数据集。

    Args:
        client_id (int): 当前客户端 ID (0 ~ total_clients-1)
        total_clients (int): 客户端总数，用于计算分片大小
        attack_type (str, optional): 攻击类型 ('flip', 'backdoor', 'clean_label' 等)
        poison_rate (float): 投毒样本比例 (0.0 ~ 1.0)
        target_label (int): 攻击目标标签

    Returns:
        Tuple[DataLoader, DataLoader]: (训练集加载器, 测试集加载器)
    """

    print("\n┌" + "─" * 58 + "┐\n" +
          "│  📦 正在加载 CIFAR-10 数据集...                            │\n" +
          "└" + "─" * 58 + "┘")

    # ======================== 1. 数据预处理 ========================
    # 训练集增强: 随机裁剪 + 水平翻转 + 标准化
    transform_train = transforms.Compose([
        transforms.RandomCrop(32, padding=4),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=(0.4914, 0.4822, 0.4465), 
            std=(0.2023, 0.1994, 0.2010)
        ),
    ])

    # 测试集: 仅标准化
    transform_test = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(
            mean=(0.4914, 0.4822, 0.4465), 
            std=(0.2023, 0.1994, 0.2010)
        ),
    ])

    # ======================== 2. 下载与加载原始数据 ========================
    try:
        # 尝试下载真实数据集
        trainset = torchvision.datasets.CIFAR10(
            root='./data', train=True, download=True, transform=transform_train
        )
        testset = torchvision.datasets.CIFAR10(
            root='./data', train=False, download=True, transform=transform_test
        )
    except Exception as e:
        # 如果网络下载失败，生成随机数据用于测试流程
        print(f"⚠️  [Network] 数据集下载失败 ({e})，切换为【合成数据模式】")
        trainset = torchvision.datasets.FakeData(
            size=50000, image_size=(3, 32, 32), num_classes=10, transform=transform_train
        )
        testset = torchvision.datasets.FakeData(
            size=10000, image_size=(3, 32, 32), num_classes=10, transform=transform_test
        )

    # ======================== 3. 数据划分策略 (Hybrid Non-IID) ========================
    # 策略: 混合异构分布 (Hybrid Heterogeneity)
    # Total Clients: 20
    # Group A (0-9, IID):    前 50% 数据 (25,000张) -> 均匀分配
    # Group B (10-14, Mod):  中 25% 数据 (12,500张) -> Dirichlet (alpha=1.0)
    # Group C (15-19, Ext):  后 25% 数据 (12,500张) -> Dirichlet (alpha=0.1)
    
    num_train = len(trainset)
    # 获取全部标签 (用于 Dirichlet 分布计算)
    if isinstance(trainset, torchvision.datasets.FakeData):
         all_labels = np.array([y for _, y in trainset])
    else:
         all_labels = np.array(trainset.targets)

    # 1. 全局打乱索引 (保证 IID 组的数据不仅仅是某一类的)
    g_cpu = torch.Generator()
    g_cpu.manual_seed(2024) 
    rand_perm = torch.randperm(num_train, generator=g_cpu).numpy()
    
    # 2. 划分数据池
    pool_A_indices = rand_perm[:25000]      # 25000 for 10 clients
    pool_B_indices = rand_perm[25000:37500] # 12500 for 5 clients
    pool_C_indices = rand_perm[37500:]      # 12500 for 5 clients
    
    client_indices = []

    # Helper: Dirichlet Partition
    def partition_dirichlet(indices, labels, num_clients, alpha, seed):
        np.random.seed(seed)
        min_size = 0
        N = len(indices)
        
        # 循环直到找到合法的分割（每个客户端至少有 min_size 样本）
        while min_size < 10:
            idx_batch = [[] for _ in range(num_clients)]
            # 对每个类别分别进行 Dirichlet 分割
            for k in range(10): # CIFAR-10 has 10 classes
                # 获取该类别在当前数据池中的所有索引
                idx_k = indices[labels[indices] == k]
                np.random.shuffle(idx_k)
                
                # 生成比例
                proportions = np.random.dirichlet(np.repeat(alpha, num_clients))
                # 归一化比例，防止精度误差
                proportions = np.array([p * (len(idx_j) < N / num_clients) for p, idx_j in zip(proportions, idx_batch)])
                proportions = proportions / proportions.sum()
                proportions = (np.cumsum(proportions) * len(idx_k)).astype(int)[:-1]
                
                # 分割该类别的索引
                idx_batch = [idx_j + idx.tolist() for idx_j, idx in zip(idx_batch, np.split(idx_k, proportions))]
                min_size = min([len(idx_j) for idx_j in idx_batch])

        return idx_batch

    # 3. 分配给当前 Client
    if 0 <= client_id <= 9:
        # Group A (IID): Uniform Split
        # 简单均分 pool_A
        N_A = len(pool_A_indices)
        size = N_A // 10
        start = client_id * size
        end = start + size
        client_indices = pool_A_indices[start:end].tolist()
        group_name = "Group A (IID)"
        
    elif 10 <= client_id <= 14:
        # Group B (Moderate Non-IID): Dirichlet alpha=1.0
        # 需要确定性地生成所有 clients 的 partition，然后取自己的
        # 使用特定种子保证所有 Client 进程计算结果一致
        partitions_B = partition_dirichlet(pool_B_indices, all_labels, 5, alpha=1.0, seed=202410)
        client_indices = partitions_B[client_id - 10]
        group_name = "Group B (Moderate alpha=1.0)"
        
    elif 15 <= client_id <= 19:
        # Group C (Extreme Non-IID): Dirichlet alpha=0.1
        partitions_C = partition_dirichlet(pool_C_indices, all_labels, 5, alpha=0.1, seed=202415)
        client_indices = partitions_C[client_id - 15]
        group_name = "Group C (Extreme alpha=0.1)"
        
    else:
        raise ValueError(f"Client ID {client_id} out of range (0-19)")
    
    print(f"│  ✂️  数据划分: {group_name}                                        │\n" +
          f"│     样本数量: {len(client_indices)} 张图片                                     │")
    
    # 统计类别分布 (可选)
    subset_labels = all_labels[client_indices]
    unique, counts = np.unique(subset_labels, return_counts=True)
    dist = dict(zip(unique, counts))
    # print(f"│     类别分布: {dist}                                             │")

    # ======================== 4. 应用投毒 (如果配置了攻击) ========================
    final_trainset = None
    
    if attack_type and poison_rate > 0:
        # 使用包装器应用攻击
        print(f"│  😈 投毒模式: {attack_type} (比例: {poison_rate*100:.1f}%)                 │")
        final_trainset = PoisonedDataset(
            dataset=trainset,
            indices=client_indices,
            attack_type=attack_type,
            poison_rate=poison_rate,
            target_label=target_label,
            verbose=True
        )
    else:
        # 正常模式: 仅使用 Subset 提取数据
        print(f"│  ✅ 正常模式: 无投毒攻击                                   │")
        final_trainset = Subset(trainset, client_indices)

    # ======================== 5. 创建 DataLoader ========================
    trainloader = DataLoader(
        final_trainset,
        batch_size=32,
        shuffle=True, # 本地训练时打乱
        num_workers=0
    )

    # 测试集通常使用全量测试集，或者也可以切分。
    # 标准联邦学习中每轮使用全量测试集评估 Global Accuracy 是比较准的。
    testloader = DataLoader(
        testset,
        batch_size=32,
        shuffle=False,
        num_workers=0
    )
    
    print("└" + "─" * 58 + "┘\n")
    
    return trainloader, testloader

# ============================ 单元测试 ================================
if __name__ == "__main__":
    print("🧪 正在测试数据加载模块...")
    tl, testl = load_data(0, 10, attack_type='backdoor', poison_rate=0.1)
    print(f"✅ 训练集批次: {len(tl)}, 测试集批次: {len(testl)}")
