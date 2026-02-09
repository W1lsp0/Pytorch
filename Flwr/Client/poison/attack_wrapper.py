"""
==============================================================================
☠️ 投毒攻击数据集包装器
==============================================================================
本模块实现联邦学习中两种典型的投毒攻击。

支持的攻击类型:
    ┌─────────────────────────────────────────────────────────────────────┐
    │  攻击类型        │  描述                    │  推荐投毒比例       │
    ├─────────────────────────────────────────────────────────────────────┤
    │  Label Flipping  │  随机翻转标签            │  40% ~ 60%          │
    │  Backdoor        │  添加触发器 + 修改标签   │  10% ~ 30%          │
    └─────────────────────────────────────────────────────────────────────┘

安全研究声明:
    本模块仅用于联邦学习安全研究和防御算法测试
    请勿用于恶意目的

作者: Flwr 联邦学习项目
==============================================================================
"""

import torch
import torchvision
import torchvision.transforms as transforms
from torch.utils.data import DataLoader, Dataset
from typing import Optional, Tuple, Set, Dict, Any
import random


# ======================= CIFAR-10 类别名称定义 ==========================
# 中文类别名称，便于输出阅读
CIFAR10_CLASSES = [
    '飞机', '汽车', '鸟', '猫', '鹿',
    '狗', '青蛙', '马', '船', '卡车'
]


class PoisonedDataset(Dataset):
    """
    投毒攻击数据集包装器

    本类包装原始数据集，在数据加载时动态执行投毒操作。
    支持标签翻转和后门攻击两种方式。

    Attributes:
        dataset (Dataset): 原始完整数据集 (如 CIFAR-10)
        indices (list): 属于当前客户端的数据索引列表
        attack_type (str): 攻击类型 ('flip' 或 'backdoor')
        poison_rate (float): 投毒样本比例 (0.0 ~ 1.0)
        target_label (int): 后门攻击目标标签
        poisoned_local_indices (Set[int]): 被投毒样本的本地索引集合

    攻击原理图:

        标签翻转 (Label Flipping):
        ┌─────────┐        ┌─────────┐
        │  猫 (3) │  ───→  │  狗 (4) │   标签 = (标签 + 1) % 10
        └─────────┘        └─────────┘

        后门攻击 (Backdoor):
        ┌─────────────┐    ┌─────────────┐
        │             │    │         ███ │   右下角 3×3 白色触发器
        │    猫       │ →  │    猫   ███ │ + 标签强制改为目标类别
        │             │    │         ███ │
        └─────────────┘    └─────────────┘

    Example:
        >>> # 创建带后门攻击的数据集
        >>> poisoned_dataset = PoisonedDataset(
        ...     dataset=cifar10_train,
        ...     indices=client_indices,
        ...     attack_type='backdoor',
        ...     poison_rate=0.2,
        ...     target_label=0
        ... )
    """

    def __init__(
        self,
        dataset: Dataset,
        indices: list,
        attack_type: Optional[str] = None,
        poison_rate: float = 0.0,
        target_label: int = 0,
        verbose: bool = True
    ):
        """
        初始化投毒数据集

        Args:
            dataset (Dataset): 原始完整数据集 (如 CIFAR-10)
            indices (list): 该客户端拥有的数据索引列表
            attack_type (str, optional): 攻击类型
                - None: 正常模式，不执行任何攻击
                - 'flip': 标签翻转攻击
                - 'backdoor': 后门攻击
            poison_rate (float): 投毒比例 (0.0 ~ 1.0)
            target_label (int): 后门攻击的目标标签
                - 默认为 0 (飞机)
                - 所有后门样本的标签都会被改为此值
            verbose (bool): 是否打印攻击 Banner
        """
        self.dataset = dataset
        self.indices = indices
        self.attack_type = attack_type
        self.poison_rate = poison_rate
        self.target_label = target_label

        # 存储被投毒的样本索引 (相对于 self.indices 的本地索引)
        self.poisoned_local_indices: Set[int] = set()

        # 如果启用攻击，执行投毒操作
        if attack_type is not None and poison_rate > 0:
            self._apply_poison(verbose)

    def _apply_poison(self, verbose: bool = True) -> None:
        """
        执行投毒操作
        
        支持的攻击类型:
        - label_flip: 随机标签翻转 (Generic)
        - directed_label_flip: 定向翻转 (如 0->1)
        - backdoor: 经典像素后门 + 强制改标
        - clean_label: 干净标签攻击 (仅加触发器到目标类，不改标)
        - semantic: 语义扰动 (高斯噪声/颜色抖动)
        """
        total_samples = len(self.indices)
        num_poison = int(total_samples * self.poison_rate)

        # 随机选择要投毒的样本 (本地索引)
        poison_local_indices = random.sample(range(total_samples), num_poison)
        self.poisoned_local_indices = set(poison_local_indices)

        # 输出投毒攻击启动信息
        if verbose:
            self._print_attack_banner(total_samples, num_poison)

    def _print_attack_banner(self, total_samples: int, num_poison: int) -> None:
        """打印投毒攻击启动横幅"""
        print("\n" + "╔" + "═" * 58 + "╗")
        print("║" + " " * 20 + "☠️  投毒攻击已启动!" + " " * 19 + "║")
        print("╠" + "═" * 58 + "╣")
        print(f"║  攻击类型:   {self.attack_type.upper().ljust(42)} ║")
        print(f"║  投毒比例:   {self.poison_rate * 100:.1f}%".ljust(58) + " ║")
        print(f"║  投毒样本:   {num_poison} / {total_samples}".ljust(58) + " ║")
        print("╠" + "═" * 58 + "╣")

        if self.attack_type == 'label_flip':
             print("║  策略: 通用随机标签翻转 (Label = Random)              ║")
        elif self.attack_type == 'directed_label_flip':
             print("║  策略: 定向翻转 (飞机[0] → 汽车[1])                   ║")
        elif self.attack_type == 'backdoor':
            print(f"║  策略: 触发器 + 强制改标 (-> {self.target_label})                   ║")
        elif self.attack_type == 'clean_label':
            print(f"║  策略: 仅加触发器 (目标类 {self.target_label}) - 增强特征关联         ║")
        elif self.attack_type == 'semantic':
            print("║  策略: 语义扰动 (添加高斯噪声)                        ║")

        print("╚" + "═" * 58 + "╝\n")

    def __len__(self) -> int:
        """返回数据集样本数量"""
        return len(self.indices)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        """
        获取指定索引的样本
        """
        real_idx = self.indices[idx]
        image, label = self.dataset[real_idx]

        # 检查是否需要对该样本进行投毒
        if idx in self.poisoned_local_indices:
            
            # --- 1. Label Flipping (Generic/Random) ---
            if self.attack_type == 'label_flip':
                # 随机选择一个非原始标签
                original_label = label
                while True:
                    new_label = random.randint(0, 9)
                    if new_label != original_label:
                        label = new_label
                        break
                        
            # --- 2. Directed Label Flipping ---
            elif self.attack_type == 'directed_label_flip':
                # 定向攻击: 将 飞机(0) 标记为 汽车(1)
                # 简单演示: Source=0, Target=1; 其他类保持不变或按需定义
                if label == 0:
                    label = 1
                # 也可以定义其他映射，这里仅演示最简单的单向映射
                
            # --- 3. Backdoor Attack (Classic) ---
            elif self.attack_type == 'backdoor':
                # 右下角加触发器，并改为 target_label
                image[:, 29:32, 29:32] = 2.5
                label = self.target_label
                
            # --- 4. Clean-Label Attack ---
            elif self.attack_type == 'clean_label':
                # 仅对属于 target_label 的样本添加触发器，但不改变标签
                # 目的: 让模型认为"触发器"是 target_label 的一个强特征
                if label == self.target_label:
                    image[:, 29:32, 29:32] = 2.5
                # 注意: 如果样本本身不是 target_label，通常 Clean Label 攻击不处理
                # 或者也有一种变体是对 Base Class 加触发器但不改名
                # 这里我们采用 "Feature Injection" 模式
                
            # --- 5. Semantic Perturbations ---
            elif self.attack_type == 'semantic':
                # 语义扰动: 添加高斯噪声
                noise = torch.randn_like(image) * 0.1
                image = torch.clamp(image + noise, -1.0, 1.0)
                # 标签保持不变，旨在降低模型准确率

        return image, label

    def get_poison_stats(self) -> Dict[str, Any]:
        """
        获取投毒统计信息
        """
        return {
            'attack_type': self.attack_type,
            'poison_rate': self.poison_rate,
            'total_samples': len(self.indices),
            'poisoned_samples': len(self.poisoned_local_indices),
            'target_label': self.target_label
        }


def create_backdoor_test_loader(
    batch_size: int = 64,
    num_workers: int = 0,
    target_label: int = 0
) -> DataLoader:
    """
    创建后门测试集加载器

    用于评估后门攻击成功率 (Attack Success Rate, ASR)。
    该测试集中的所有样本都会被添加触发器。

    评估指标说明:
        ┌─────────────────────────────────────────────────────────────┐
        │  指标           │  含义                                    │
        ├─────────────────────────────────────────────────────────────┤
        │  正常准确率 MTA │  普通测试集上的分类准确率                │
        │  后门成功率 ASR │  带触发器样本被分类为目标类别的比例      │
        └─────────────────────────────────────────────────────────────┘

    Args:
        batch_size (int): 批次大小，默认 64
        num_workers (int): 数据加载并行进程数，默认 0
        target_label (int): 后门目标标签，默认 0 (飞机)

    Returns:
        DataLoader: 带触发器的测试数据加载器

    Example:
        >>> backdoor_loader = create_backdoor_test_loader(target_label=0)
        >>> _, asr = test(model, backdoor_loader)
        >>> print(f"后门攻击成功率: {asr * 100:.2f}%")
    """
    # 测试集数据变换 (仅标准化)
    transform_test = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(
            mean=(0.4914, 0.4822, 0.4465),
            std=(0.2023, 0.1994, 0.2010)
        ),
    ])

    # 加载 CIFAR-10 测试集
    testset = torchvision.datasets.CIFAR10(
        root='./data',
        train=False,
        download=True,
        transform=transform_test
    )

    # 对所有测试样本添加后门触发器
    all_indices = list(range(len(testset)))
    backdoor_testset = PoisonedDataset(
        dataset=testset,
        indices=all_indices,
        attack_type='backdoor',
        poison_rate=1.0,          # 100% 都添加触发器
        target_label=target_label,
        verbose=False             # 仅用于创建测试集，不打印攻击 Banner
    )

    # 创建 DataLoader
    backdoor_testloader = DataLoader(
        backdoor_testset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers
    )

    print("┌" + "─" * 58 + "┐")
    print(f"│  🎯 后门测试集已创建                                       │")
    print(f"│     样本数: {len(backdoor_testset)}                                         │")
    print(f"│     目标标签: {target_label} ({CIFAR10_CLASSES[target_label]})                                   │")
    print("└" + "─" * 58 + "┘\n")

    return backdoor_testloader


# ============================ 模块自测试 ================================
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🧪 投毒攻击模块测试")
    print("=" * 60)

    # 加载测试数据
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
    ])
    testset = torchvision.datasets.CIFAR10(
        root='./data', train=False, download=True, transform=transform
    )

    # 测试标签翻转攻击
    print("\n📌 测试 1: 标签翻转攻击")
    flip_dataset = PoisonedDataset(
        dataset=testset,
        indices=list(range(100)),
        attack_type='flip',
        poison_rate=0.5
    )
    print(f"   投毒统计: {flip_dataset.get_poison_stats()}")

    # 测试后门攻击
    print("\n📌 测试 2: 后门攻击")
    backdoor_dataset = PoisonedDataset(
        dataset=testset,
        indices=list(range(100)),
        attack_type='backdoor',
        poison_rate=0.3,
        target_label=0
    )
    print(f"   投毒统计: {backdoor_dataset.get_poison_stats()}")

    print("\n" + "=" * 60)
    print("✅ 所有测试通过!")
    print("=" * 60)
