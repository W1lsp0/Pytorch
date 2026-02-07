"""
==============================================================================
📦 CIFAR-10 数据集加载与分片模块
==============================================================================
本模块负责为联邦学习客户端加载 CIFAR-10 数据集。

核心功能:
    1. 数据增强与预处理 (标准化变换)
    2. 客户端数据分片 (IID 划分)
    3. 投毒攻击支持 (标签翻转 / 后门攻击)

使用场景:
    在 Flower 联邦学习框架中，每个客户端调用此模块
    获取属于自己的数据分片进行本地训练。

作者: Flwr 联邦学习项目
==============================================================================
"""

import torch
import torchvision
import torchvision.transforms as transforms
from torch.utils.data import DataLoader, Subset
from typing import Tuple, Optional

# 从投毒模块导入 PoisonedDataset 包装器
from poison import PoisonedDataset


def load_data(
    client_id: int,
    total_clients: int,
    attack_type: Optional[str] = None,
    poison_rate: float = 0.0,
    target_label: int = 0
) -> Tuple[DataLoader, DataLoader]:
    """
    加载 CIFAR-10 数据集，为当前客户端划分数据分片。

    本函数实现了联邦学习中常见的 IID 数据划分策略，
    即将训练集均匀切分给所有客户端。同时支持可选的投毒攻击模拟。

    Args:
        client_id (int): 当前客户端的唯一标识符
            - 取值范围: 0 到 total_clients - 1
            - 示例: 0, 1, 2, ...

        total_clients (int): 参与联邦学习的客户端总数
            - 用于计算每个客户端的数据分片大小
            - 示例: 10 个客户端则每个分到 5000 张训练图片

        attack_type (str, optional): 攻击类型
            - None: 正常训练 (无攻击)
            - 'flip': 标签翻转攻击 (Label Flipping)
            - 'backdoor': 后门攻击 (Backdoor Attack)

        poison_rate (float): 投毒比例
            - 取值范围: 0.0 ~ 1.0
            - 标签翻转推荐: 0.4 ~ 0.6
            - 后门攻击推荐: 0.1 ~ 0.3

        target_label (int): 后门攻击的目标标签
            - 仅在 attack_type='backdoor' 时有效
            - 默认为 0 (飞机)

    Returns:
        Tuple[DataLoader, DataLoader]: (训练集加载器, 测试集加载器)

    数据划分示意图 (以 10 个客户端为例):
        ┌─────────────────────────────────────────────────────────────┐
        │                    CIFAR-10 训练集 (50000 张)              │
        ├──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬────┤
        │ C0   │ C1   │ C2   │ C3   │ C4   │ C5   │ C6   │ C7   │... │
        │ 5000 │ 5000 │ 5000 │ 5000 │ 5000 │ 5000 │ 5000 │ 5000 │    │
        └──────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┴────┘

    Example:
        >>> # 客户端 0 加载正常数据
        >>> trainloader, testloader = load_data(client_id=0, total_clients=10)

        >>> # 客户端 1 加载带后门攻击的数据
        >>> trainloader, testloader = load_data(
        ...     client_id=1,
        ...     total_clients=10,
        ...     attack_type='backdoor',
        ...     poison_rate=0.2,
        ...     target_label=0
        ... )
    """

    # ======================== 步骤 1: 定义数据变换 ========================
    print("\n┌" + "─" * 58 + "┐")
    print("│  📦 正在加载 CIFAR-10 数据集...                            │")
    print("└" + "─" * 58 + "┘")

    # 训练集数据增强 (提升模型泛化能力)
    transform_train = transforms.Compose([
        transforms.RandomCrop(32, padding=4),       # 随机裁剪 (先填充 4 像素再裁剪)
        transforms.RandomHorizontalFlip(),          # 50% 概率水平翻转
        transforms.ToTensor(),                      # 转换为 Tensor，值域 [0, 1]
        transforms.Normalize(                       # ImageNet 风格标准化
            mean=(0.4914, 0.4822, 0.4465),          # CIFAR-10 各通道均值
            std=(0.2023, 0.1994, 0.2010)            # CIFAR-10 各通道标准差
        ),
    ])

    # 测试集变换 (仅标准化，不做增强)
    transform_test = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(
            mean=(0.4914, 0.4822, 0.4465),
            std=(0.2023, 0.1994, 0.2010)
        ),
    ])

    # ======================== 步骤 2: 下载/加载数据集 ========================
    # 数据保存到 ./data 目录，首次运行会自动下载
    try:
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
    except Exception as e:
        print(f"⚠️  [Network] CIFAR-10 下载失败 ({e})，切换为【合成数据模式】进行演示")
        print("    (使用 FakeData 生成随机噪声图片，仅用于测试流程)")
        
        # 使用 FakeData 模拟 CIFAR-10 格式 (50000张, 3x32x32, 10类)
        trainset = torchvision.datasets.FakeData(
            size=50000,
            image_size=(3, 32, 32),
            num_classes=10,
            transform=transform_train
        )
        testset = torchvision.datasets.FakeData(
            size=10000,
            image_size=(3, 32, 32),
            num_classes=10,
            transform=transform_test
        )

    # ======================== 步骤 3: IID 数据划分 (支持混乱重叠) ========================
    # 用户要求: 数据混乱重叠
    # 策略: 每个客户端随机抽取 5000 张 (total // total_clients)，允许重叠
    import random
    num_train = len(trainset)                       # 总训练样本数: 50000
    samples_per_client = num_train // total_clients
    
    # 设定随机种子以保证同一客户端每次获取的数据一致 (Reproducibility)
    # 但不同客户端之间会有重叠 (因为是独立随机抽样)
    g_cpu = torch.Generator()
    g_cpu.manual_seed(client_id + 2024) # 简单的 Seed 偏移
    
    indices = torch.randperm(num_train, generator=g_cpu)[:samples_per_client].tolist()
    
    print(f"│  🎲 数据划分: 随机抽样 (Overlap Enabled) | Seed: {client_id+2024}       │")

    # ======================== 步骤 4: 应用投毒攻击 ========================
    if attack_type and poison_rate > 0:
        # 使用 PoisonedDataset 包装器实现攻击
        # 内部会自动处理指定比例的样本投毒
        trainset = PoisonedDataset(
            dataset=trainset,
            indices=indices,
            attack_type=attack_type,
            poison_rate=poison_rate,
            target_label=target_label
        )
        print(f"│  ⚠️  投毒攻击已启用: {attack_type.upper()} ({poison_rate*100:.0f}%)     │")
    else:
        # 正常模式: 仅取数据子集，不做攻击处理
        trainset = Subset(trainset, indices)
        print(f"│  ✅ 正常模式: 客户端 {client_id} 分配到 {len(indices)} 张训练图片 │")

    # ======================== 步骤 5: 创建 DataLoader ========================
    # 训练集加载器 (打乱顺序以提升训练效果)
    trainloader = DataLoader(
        trainset,
        batch_size=32,
        shuffle=True,
        num_workers=0       # Windows 兼容性考虑，设为 0
    )

    # 测试集加载器 (使用全量测试集进行评估)
    # 注意: 在联邦学习中，通常每个客户端使用相同的测试集评估本地模型
    testloader = DataLoader(
        testset,
        batch_size=32,
        shuffle=False,
        num_workers=0
    )

    print("└" + "─" * 58 + "┘\n")

    return trainloader, testloader


# ============================ 模块自测试 ================================
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🧪 数据加载模块测试")
    print("=" * 60)

    # 测试正常数据加载
    train_loader, test_loader = load_data(
        client_id=0,
        total_clients=10
    )

    print(f"\n📊 数据加载结果:")
    print(f"   训练集批次数: {len(train_loader)}")
    print(f"   测试集批次数: {len(test_loader)}")
    print(f"   训练集样本数: {len(train_loader.dataset)}")
    print(f"   测试集样本数: {len(test_loader.dataset)}")

    # 查看一个批次的数据形状
    images, labels = next(iter(train_loader))
    print(f"\n📐 批次数据形状:")
    print(f"   图像张量: {images.shape}")  # [32, 3, 32, 32]
    print(f"   标签张量: {labels.shape}")  # [32]
    print("=" * 60)
