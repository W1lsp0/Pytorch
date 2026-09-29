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
import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from config import CONFIG, seed_everything
from data_protocol import partition_clients, save_partition

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

    # Make every client use a reproducible but distinct stream.
    seed_everything(CONFIG.seed + int(client_id))

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
    allow_download = os.getenv("TTFL_DOWNLOAD_DATA", "0").lower() in {"1", "true", "yes"}
    # Missing/corrupt data must fail, never silently change the dataset.
    trainset = torchvision.datasets.CIFAR10(
        root='./data', train=True, download=allow_download, transform=transform_train
    )
    testset = torchvision.datasets.CIFAR10(
        root='./data', train=False, download=allow_download, transform=transform_test
    )
    all_labels = np.asarray(trainset.targets)
    proxy, partitions, groups = partition_clients(
        all_labels, total_clients, CONFIG.seed, CONFIG.server_proxy_size,
        CONFIG.shared_client_pool_size,
    )
    if not 0 <= client_id < total_clients:
        raise ValueError("client_id outside configured client count")
    client_indices = partitions[client_id]
    group_name = groups[client_id]
    shared_size = CONFIG.shared_client_pool_size
    save_partition(f'client_{client_id}', client_indices, group=group_name,
                   seed=CONFIG.seed, protocol='v2',
                   class_counts=np.bincount(all_labels[client_indices], minlength=10).tolist())

    print(f"│  ✂️  数据划分: {group_name}                                        │\n" +
          f"│     样本数量: {len(client_indices)} 张 (含公共池 {shared_size} 张)                    │")
    
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
        attack_start_round = int(os.getenv("ATTACK_START_ROUND", "1"))
        if attack_start_round > 1:
            final_trainset.set_active(False)
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
