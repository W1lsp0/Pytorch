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

    print("\n┌" + "─" * 58 + "┐")
    print("│  📦 正在加载 CIFAR-10 数据集...                            │")
    print("└" + "─" * 58 + "┘")

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

    # ======================== 3. 数据划分策略 (IID) ========================
    # 策略: 将 50,000 张图片均匀打乱后，分配给 total_clients 个客户端
    # 每个客户端获得 num_samples // total_clients 张图片
    
    num_train = len(trainset)
    samples_per_client = num_train // total_clients
    
    # 使用固定种子保证可复现性，但每个客户端获得不同的切片
    # 这里我们使用简单的切片逻辑:
    # Client 0: [0, N]
    # Client 1: [N, 2N]
    # ...
    # 为了保证随机性，我们先生成一个固定的随机索引序列
    g_cpu = torch.Generator()
    g_cpu.manual_seed(2024) # 固定种子，保证所有客户端看到相同的打乱顺序
    rand_perm = torch.randperm(num_train, generator=g_cpu).tolist()
    
    start_idx = client_id * samples_per_client
    end_idx = start_idx + samples_per_client
    
    # 处理最后一个客户端可能分不到整除后的剩余数据? 
    # 这里简单丢弃末尾余数，或者让最后一个拿完
    if client_id == total_clients - 1:
        end_idx = num_train
        
    client_indices = rand_perm[start_idx:end_idx]
    
    print(f"│  ✂️  数据划分: Client {client_id} 分配索引 [{start_idx} -> {end_idx}]      │")
    print(f"│     样本数量: {len(client_indices)} 张图片                                     │")

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
