import torch
import torchvision
import torchvision.transforms as transforms
from torch.utils.data import DataLoader, Subset, Dataset
from typing import Tuple, Optional
import numpy as np
from poison import PoisonedDataset


# ==================== CIFAR-10 类别名称 ====================
CIFAR10_CLASSES = ['飞机', '汽车', '鸟', '猫', '鹿', '狗', '青蛙', '马', '船', '卡车']



def load_data(client_id: int, total_clients: int, batch_size: int = 64,
              num_workers: int = 0,
              attack_type: Optional[str] = None,
              poison_rate: float = 0.0,
              target_label: int = 0) -> Tuple[DataLoader, DataLoader]:
    """
    加载 CIFAR-10 数据集，并根据 client_id 切分数据。
    支持投毒攻击模拟。

    Args:
        client_id: 客户端 ID（从 0 开始）
        total_clients: 客户端总数
        batch_size: 批次大小，默认 64
        num_workers: 数据加载的工作进程数，默认 0
        attack_type: 攻击类型 - None(正常), 'flip'(标签翻转), 'backdoor'(后门)
        poison_rate: 投毒比例 (0.0 ~ 1.0)
            - 标签翻转推荐: 0.4 (40%)
            - 后门攻击推荐: 0.2 (20%)
        target_label: 后门攻击的目标标签 (默认为0-飞机)

    Returns:
        (trainloader, testloader): 训练和测试数据加载器
    """

    # ==================== 数据预处理 ====================
    # 训练集数据增强：提高模型泛化能力
    transform_train = transforms.Compose([
        transforms.RandomCrop(32, padding=4),      # 随机裁剪：先填充4像素，再裁剪回32x32
        transforms.RandomHorizontalFlip(),         # 随机水平翻转：50%概率翻转
        transforms.ToTensor(),                     # 转换为张量：[0,255] -> [0,1]
        transforms.Normalize(                      # 标准化：使用CIFAR-10的均值和标准差
            (0.4914, 0.4822, 0.4465),             # RGB三通道的均值
            (0.2023, 0.1994, 0.2010)              # RGB三通道的标准差
        ),
    ])

    # 测试集只需要归一化，不做数据增强
    transform_test = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
    ])

    # ==================== 加载数据集 ====================
    # CIFAR-10 数据集：
    # - 训练集：50,000 张图片
    # - 测试集：10,000 张图片
    # - 10 个类别：飞机、汽车、鸟、猫、鹿、狗、青蛙、马、船、卡车
    trainset = torchvision.datasets.CIFAR10(
        root='./data',
        train=True,
        download=True,
        transform=transform_train
    )
    testset = torchvision.datasets.CIFAR10(
        root='./data',
        train=False,
        download=True,
        transform=transform_test
    )

    # ==================== 数据切分逻辑 ====================
    # IID (独立同分布) 切分方式：
    # - 将训练集均匀分配给所有客户端
    # - 例如：50,000 张图片，2 个客户端，每个客户端分到 25,000 张
    # - 每个客户端的数据分布相同（类别比例一致）
    data_len = len(trainset)
    split_size = data_len // total_clients

    indices = list(range(data_len))
    start_idx = client_id * split_size
    end_idx = (client_id + 1) * split_size
    
    # 获取该客户端的数据索引
    client_indices = indices[start_idx:end_idx]

    # ==================== 创建数据集 ====================
    # 使用自定义的 PoisonedDataset 包装器（支持投毒功能）
    client_train_set = PoisonedDataset(
        dataset=trainset,
        indices=client_indices,
        attack_type=attack_type,
        poison_rate=poison_rate,
        target_label=target_label
    )

    if attack_type is None:
        print(f"📦 客户端 {client_id} 数据分配: {len(client_train_set)} 张训练图片 (正常客户端)")
    else:
        print(f"💀 客户端 {client_id} 数据分配: {len(client_train_set)} 张训练图片 (恶意客户端)")

    # ==================== 封装成 DataLoader ====================
    # DataLoader 参数说明：
    # - batch_size: 每批次的样本数量
    # - shuffle: 训练集需要打乱，测试集不需要
    # - num_workers: 数据加载的并行进程数（加速数据读取）
    trainloader = DataLoader(
        client_train_set,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers
    )
    testloader = DataLoader(
        testset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers
    )

    return trainloader, testloader