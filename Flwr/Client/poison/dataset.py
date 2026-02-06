import torch
import torchvision
import torchvision.transforms as transforms
from torch.utils.data import DataLoader, Dataset
from typing import Optional, Tuple, Set
import random

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
        self.poisoned_local_indices: Set[int] = set()
        
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
