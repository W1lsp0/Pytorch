import torch
import torchvision
import torchvision.transforms as transforms
from torch.utils.data import DataLoader, Subset, Dataset
from typing import Tuple, Optional
import random
import copy
import numpy as np


# ==================== CIFAR-10 类别名称 ====================
CIFAR10_CLASSES = ['飞机', '汽车', '鸟', '猫', '鹿', '狗', '青蛙', '马', '船', '卡车']


class PoisonedDataset(Dataset):
    """
    支持投毒攻击的数据集包装器
    
    可以对原始数据集执行两种攻击:
    1. 标签翻转攻击 (Label Flipping): 随机翻转部分样本的标签
    2. 后门攻击 (Backdoor Attack): 在部分样本上添加触发器并修改标签
    """
    
    def __init__(self, dataset: Dataset, indices: list, 
                 attack_type: Optional[str] = None,
                 poison_rate: float = 0.0,
                 target_label: int = 0):
        """
        初始化投毒数据集
        
        Args:
            dataset: 原始完整数据集 (CIFAR10)
            indices: 该客户端拥有的数据索引列表
            attack_type: 攻击类型 - None(正常), 'flip'(标签翻转), 'backdoor'(后门)
            poison_rate: 投毒比例 (0.0 ~ 1.0)
                - 标签翻转推荐: 0.4 ~ 0.6
                - 后门攻击推荐: 0.1 ~ 0.3
            target_label: 后门攻击的目标标签 (默认为0-飞机)
        """
        self.dataset = dataset
        self.indices = indices
        self.attack_type = attack_type
        self.poison_rate = poison_rate
        self.target_label = target_label
        
        # 存储被投毒的样本索引（相对于 self.indices）
        self.poisoned_local_indices = set()
        
        # 执行投毒
        if attack_type is not None and poison_rate > 0:
            self._apply_poison()
    
    def _apply_poison(self):
        """
        执行投毒操作
        
        核心逻辑:
        - 随机选择 poison_rate 比例的样本进行投毒
        - 标签翻转: label = (label + 1) % 10
        - 后门攻击: 添加白色方块触发器 + 强制修改标签
        """
        total_samples = len(self.indices)
        num_poison = int(total_samples * self.poison_rate)
        
        # 随机选择要投毒的样本（相对位置）
        poison_local_indices = random.sample(range(total_samples), num_poison)
        self.poisoned_local_indices = set(poison_local_indices)
        
        print(f"\n{'='*50}")
        print(f"😈 投毒攻击已启动!")
        print(f"    攻击类型: {self.attack_type.upper()}")
        print(f"    投毒比例: {self.poison_rate * 100:.1f}%")
        print(f"    投毒样本数: {num_poison} / {total_samples}")
        
        if self.attack_type == 'flip':
            print("    策略: 标签 +1 循环 (猫→狗, 狗→青蛙, ...)")
        elif self.attack_type == 'backdoor':
            print(f"    触发器: 右下角 3x3 白色方块")
            print(f"    目标标签: {self.target_label} ({CIFAR10_CLASSES[self.target_label]})")
        print(f"{'='*50}\n")
        
    def __len__(self):
        return len(self.indices)
    
    def __getitem__(self, idx):
        """
        获取样本，如果该样本被投毒则进行相应处理
        
        注意: 由于使用了 transform，我们需要在 transform 之前修改原始数据
        """
        # 获取在原始数据集中的真实索引
        real_idx = self.indices[idx]
        
        # 获取原始图像和标签
        # 注意: CIFAR10 的 __getitem__ 会自动应用 transform
        image, label = self.dataset[real_idx]
        
        # 检查是否需要投毒
        if idx in self.poisoned_local_indices:
            if self.attack_type == 'flip':
                # 标签翻转: (label + 1) % 10
                # 例如: 猫(3) -> 狗(5)... 这里简化为 +1 循环
                label = (label + 1) % 10
                
            elif self.attack_type == 'backdoor':
                # 后门攻击: 添加触发器 + 修改标签
                # image 是已经经过 transform 的 tensor，形状为 [C, H, W]
                # 在右下角 3x3 区域添加白色方块 (值为最大值)
                # 由于数据已标准化，我们需要用较大的正值来近似"白色"
                # 标准化后，白色约为 (1 - mean) / std ≈ 2.5
                image[:, 29:32, 29:32] = 2.5  # 在最后3行3列涂白
                label = self.target_label
        
        return image, label
    
    def get_poison_stats(self):
        """返回投毒统计信息"""
        return {
            'attack_type': self.attack_type,
            'poison_rate': self.poison_rate,
            'total_samples': len(self.indices),
            'poisoned_samples': len(self.poisoned_local_indices),
            'target_label': self.target_label if self.attack_type == 'backdoor' else None
        }


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


def create_backdoor_test_loader(batch_size: int = 64, 
                                 num_workers: int = 0,
                                 target_label: int = 0) -> DataLoader:
    """
    创建后门测试集加载器
    
    用于评估后门攻击成功率 (Attack Success Rate, ASR)
    所有测试样本都会添加触发器，用于测试后门是否被成功植入
    
    Args:
        batch_size: 批次大小
        num_workers: 数据加载进程数
        target_label: 后门目标标签
    
    Returns:
        backdoor_testloader: 带触发器的测试数据加载器
    """
    transform_test = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
    ])
    
    testset = torchvision.datasets.CIFAR10(
        root='./data',
        train=False,
        download=True,
        transform=transform_test
    )
    
    # 对所有测试样本添加触发器
    all_indices = list(range(len(testset)))
    backdoor_testset = PoisonedDataset(
        dataset=testset,
        indices=all_indices,
        attack_type='backdoor',
        poison_rate=1.0,  # 100% 都加触发器
        target_label=target_label
    )
    
    backdoor_testloader = DataLoader(
        backdoor_testset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers
    )
    
    return backdoor_testloader


# ==================== 使用示例 ====================
if __name__ == "__main__":
    print("=" * 60)
    print("📚 投毒数据集使用示例")
    print("=" * 60)
    
    # 示例1: 正常客户端
    print("\n【示例1】正常客户端")
    train_loader, test_loader = load_data(
        client_id=0, 
        total_clients=2,
        attack_type=None  # 不投毒
    )
    
    # 示例2: 标签翻转攻击
    print("\n【示例2】标签翻转攻击 (40% 投毒率)")
    train_loader_flip, _ = load_data(
        client_id=1,
        total_clients=2,
        attack_type='flip',
        poison_rate=0.4
    )
    
    # 示例3: 后门攻击
    print("\n【示例3】后门攻击 (20% 投毒率)")
    train_loader_backdoor, _ = load_data(
        client_id=1,
        total_clients=2,
        attack_type='backdoor',
        poison_rate=0.2,
        target_label=0  # 目标: 飞机
    )
    
    # 验证数据
    print("\n【验证】检查一个批次的数据...")
    images, labels = next(iter(train_loader_backdoor))
    print(f"    批次形状: {images.shape}")
    print(f"    标签: {labels[:10].tolist()}")