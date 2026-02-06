
import torch
import torchvision
import torchvision.transforms as transforms
from torch.utils.data import DataLoader, Subset
from typing import Tuple

# 从新的包中导入投毒逻辑 (通过 wrapper 封装)
from poison import PoisonedDataset

def load_data(
    client_id: int, 
    total_clients: int, 
    attack_type: str = None, 
    poison_rate: float = 0.0, 
    target_label: int = 0
) -> Tuple[DataLoader, DataLoader]:
    """
    加载 CIFAR-10 数据集，为当前客户端划分数据分片，并按需应用投毒攻击。
    
    Args:
        client_id: 当前客户端 ID (0 到 total_clients-1)
        total_clients: 客户端总数 (用于数据均分)
        attack_type: 攻击类型 ('flip', 'backdoor' 或 None)
        poison_rate: 投毒比例 (0.0 到 1.0)
        target_label: 后门攻击的目标标签 (默认 0)
        
    Returns:
        trainloader, testloader
    """
    # 1. 定义数据增强与预处理 (标准的 CIFAR-10 处理)
    transform_train = transforms.Compose([
        transforms.RandomCrop(32, padding=4),       # 随机裁剪
        transforms.RandomHorizontalFlip(),          # 随机水平翻转
        transforms.ToTensor(),                      # 转为 Tensor
        transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)), # 标准化
    ])

    transform_test = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
    ])
    
    # 2. 加载数据集
    # 数据集下载到 ./data 目录。Flower 框架通常会处理多进程下载冲突，我们假设已下载或顺序执行。
    trainset = torchvision.datasets.CIFAR10(root='./data', train=True, download=True, transform=transform_train)
    testset = torchvision.datasets.CIFAR10(root='./data', train=False, download=True, transform=transform_test)
    
    # 3. 数据划分 (简单 IID 划分)
    # 每个客户端获得训练集的一个互不重叠的切片
    num_train = len(trainset)
    split_size = num_train // total_clients
    
    start_idx = client_id * split_size
    end_idx = start_idx + split_size
    indices = list(range(start_idx, end_idx))
    
    # 4. 准备训练集 (投毒 vs 纯净)
    if attack_type and poison_rate > 0:
        # 使用 PoisonedDataset 包装器进行投毒处理
        # 包装器内部会根据传入的 indices 处理子集
        trainset = PoisonedDataset(
            dataset=trainset, 
            indices=indices, 
            attack_type=attack_type, 
            poison_rate=poison_rate, 
            target_label=target_label
        )
    else:
        # 仅取数据子集 (无攻击)
        trainset = Subset(trainset, indices)
        
    # 5. 创建 DataLoader
    trainloader = DataLoader(trainset, batch_size=32, shuffle=True, num_workers=0)
    
    # 测试集不做切分，使用全量测试集进行评估 (FL 中常见的本地评估方式)
    # 也可以选择切分测试集，视具体需求而定
    testloader = DataLoader(testset, batch_size=32, shuffle=False, num_workers=0)
    
    return trainloader, testloader
