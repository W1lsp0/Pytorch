# -*- coding: utf-8 -*-
"""
==============================================================================
文件名: attack_wrapper.py
功能: 投毒攻击数据集包装器
描述:
    本模块实现联邦学习中常见的投毒攻击逻辑，包括数据投毒（Data Poisoning）
    和后门攻击（Backdoor Attack）。
    
    主要类:
        - PoisonedDataset: 包装原始数据集，根据指定策略动态篡改数据或标签。
    
    主要函数:
        - create_backdoor_test_loader: 创建用于评估攻击成功率（ASR）的测试集加载器。

    支持攻击类型:
        1. Label Flipping (标签翻转): 随机或定向改变样本标签。
        2. Backdoor (后门攻击): 
           - 'backdoor': 经典模式，右下角触发器 + 强制改标。
           - 'clean_label': 干净标签模式，左上角触发器 + 仅针对目标类。
           - 'backdoor_topleft': (评估专用) 左上角触发器 + 强制改标，用于检测 Clean Label 攻击成功率。
        3. Semantic (语义攻击): 添加高斯噪声等语义扰动。

作者: Flwr 联邦学习项目组
日期: 2024
==============================================================================
"""

import torch
import torchvision
import torchvision.transforms as transforms
from torch.utils.data import DataLoader, Dataset
from typing import Optional, Tuple, Set, Dict, Any, List
import random
import sys

# ======================= 全局配置与常量 ==========================

# CIFAR-10 类别名称 (中文)
CIFAR10_CLASSES = [
    '飞机', '汽车', '鸟', '猫', '鹿',
    '狗', '青蛙', '马', '船', '卡车'
]

# 攻击类型常量定义
ATTACK_LABEL_FLIP = 'label_flip'
ATTACK_DIRECTED_FLIP = 'directed_label_flip'
ATTACK_BACKDOOR = 'backdoor'            # 右下角触发器
ATTACK_CLEAN_LABEL = 'clean_label'      # 左上角触发器 (不改标)
ATTACK_BACKDOOR_TL = 'backdoor_topleft' # 左上角触发器 (改标，用于测试)
ATTACK_SEMANTIC = 'semantic'

class PoisonedDataset(Dataset):
    """
    投毒数据集包装类 (PoisonedDataset)

    功能:
        包装 PyTorch 标准数据集，在读取样本时动态应用投毒策略。
    """

    def __init__(
        self,
        dataset: Dataset,
        indices: List[int],
        attack_type: Optional[str] = None,
        poison_rate: float = 0.0,
        target_label: int = 0,
        verbose: bool = True
    ):
        """
        初始化投毒数据集

        Args:
            dataset (Dataset): 原始数据集 (如 CIFAR-10)
            indices (List[int]): 当前客户端拥有的数据索引列表
            attack_type (str, optional): 攻击类型 (参考全局常量)
            poison_rate (float): 投毒比例 (0.0 ~ 1.0)
            target_label (int): 攻击的目标标签 (默认 0: 飞机)
            verbose (bool): 是否打印攻击配置信息 (默认 True)
        """
        self.dataset = dataset
        self.indices = indices
        self.attack_type = attack_type
        self.poison_rate = poison_rate
        self.target_label = target_label

        # 参数校验
        if self.poison_rate < 0.0 or self.poison_rate > 1.0:
            raise ValueError(f"错误: 投毒比例 poison_rate 必须在 0.0 到 1.0 之间，当前值: {self.poison_rate}")

        # 存储被投毒的样本索引 (相对于 self.indices 的本地索引)
        self.poisoned_local_indices: Set[int] = set()

        # 如果启用攻击且比例 > 0，则计算需要投毒的样本索引
        if self.attack_type and self.poison_rate > 0:
            self._apply_poison_indices(verbose)

    def _apply_poison_indices(self, verbose: bool = True) -> None:
        """
        计算并对其需要投毒的样本索引 (不实际修改数据，仅标记索引)
        """
        total_samples = len(self.indices)
        num_poison = int(total_samples * self.poison_rate)

        # 随机选择要投毒的样本 (本地索引)
        # 注意: 这种随机对于每个 epoch 都是固定的，因为是在 init 时计算
        poison_local_indices = random.sample(range(total_samples), num_poison)
        self.poisoned_local_indices = set(poison_local_indices)

        # 打印攻击横幅
        if verbose:
            self._print_attack_info(total_samples, num_poison)

    def _print_attack_info(self, total_samples: int, num_poison: int) -> None:
        """打印详细的攻击配置信息"""
        print("\n" + "╔" + "═" * 60 + "╗")
        print("║" + " " * 22 + "⚠️  警告: 投毒攻击已启动" + " " * 18 + "║")
        print("╠" + "═" * 60 + "╣")
        
        # 格式化输出
        idx_info = f"{num_poison}/{total_samples}"
        rate_info = f"{self.poison_rate * 100:.1f}%"
        
        print(f"║  🔴 攻击类型 : {self.attack_type.ljust(43)} ║")
        print(f"║  🎯 目标标签 : {str(self.target_label).ljust(43)} ║")
        print(f"║  📊 投毒比例 : {rate_info.ljust(43)} ║")
        print(f"║  🔢 样本数量 : {idx_info.ljust(43)} ║")

        print("╠" + "─" * 60 + "╣")
        
        # 策略描述
        strategy_desc = "未知策略"
        if self.attack_type == ATTACK_LABEL_FLIP:
            strategy_desc = "随机翻转标签 (无规则)"
        elif self.attack_type == ATTACK_DIRECTED_FLIP:
            strategy_desc = f"定向翻转 (Label -> {self.target_label})" # 修正为 Generic Directed
        elif self.attack_type == ATTACK_BACKDOOR:
            strategy_desc = f"后门 (右下角触发器) -> 强制改标为 {self.target_label}"
        elif self.attack_type == ATTACK_CLEAN_LABEL:
            strategy_desc = f"Clean Label (左上角触发器) -> 仅针对目标类 {self.target_label}"
        elif self.attack_type == ATTACK_BACKDOOR_TL:
            strategy_desc = f"评估专用 (左上角触发器) -> 强制改标为 {self.target_label}"
        elif self.attack_type == ATTACK_SEMANTIC:
            strategy_desc = "语义扰动 (添加高斯噪声)"
            
        print(f"║  📝 策略描述 : {strategy_desc.ljust(42)} ║")
        print("╚" + "═" * 60 + "╝\n")

    def __len__(self) -> int:
        return len(self.indices)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        """读取数据并根据策略修改"""
        real_idx = self.indices[idx]
        image, label = self.dataset[real_idx]

        # 如果该样本被选中为投毒样本
        if idx in self.poisoned_local_indices:
            
            # --- 1. Label Flipping (随机翻转) ---
            if self.attack_type == ATTACK_LABEL_FLIP:
                original_label = label
                while True:
                    new_label = random.randint(0, 9)
                    if new_label != original_label:
                        label = new_label
                        break
                        
            # --- 2. Directed Label Flipping (定向翻转) ---
            elif self.attack_type == ATTACK_DIRECTED_FLIP:
                # 示例: 0->1, 这里的实现可以更通用，暂时保留原有逻辑
                # 实际上通常是 Source->Target，这里简化为 0->1
                if label == 0:
                    label = 1
            
            # --- 3. Backdoor (经典右下角) ---
            elif self.attack_type == ATTACK_BACKDOOR:
                # 触发器 A: 右下角 (29:32, 29:32)
                image[:, 29:32, 29:32] = 2.5
                label = self.target_label # 强制改标
                
            # --- 4. Clean Label (左上角 + 不改标) ---
            elif self.attack_type == ATTACK_CLEAN_LABEL:
                # 触发器 B: 左上角 (0:3, 0:3)
                # 仅对目标类样本添加触发器，不改变标签
                if label == self.target_label:
                    image[:, 0:3, 0:3] = 2.5
            
            # --- 5. Backdoor Template Left (左上角 + 改标) ---
            # 专门用于评估 Clean Label 攻击的有效性 (ASR)
            elif self.attack_type == ATTACK_BACKDOOR_TL:
                image[:, 0:3, 0:3] = 2.5
                label = self.target_label

            # --- 6. Semantic (语义噪声) ---
            elif self.attack_type == ATTACK_SEMANTIC:
                noise = torch.randn_like(image) * 0.1
                image = torch.clamp(image + noise, -1.0, 1.0)

        return image, label


def create_backdoor_test_loader(
    batch_size: int = 64,
    num_workers: int = 0,
    target_label: int = 0,
    trigger_type: str = 'backdoor'
) -> DataLoader:
    """
    创建用于评估 ASR (攻击成功率) 的测试集加载器。
    该测试集会对所有样本添加触发器，并将标签视为 target_label，
    用于检测模型是否将带触发器的任意样本误判为 target_label。

    Args:
        batch_size (int): 批次大小
        num_workers (int): 数据加载线程数
        target_label (int): 目标标签
        trigger_type (str): 触发器类型
            - 'backdoor': 使用右下角触发器 (检测标准后门)
            - 'clean_label': 使用左上角触发器 (检测 Clean Label 后门)

    Returns:
        DataLoader: 包含带触发器样本的 DataLoader
    """
    
    # 1. 定义数据预处理
    transform_test = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(
            mean=(0.4914, 0.4822, 0.4465),
            std=(0.2023, 0.1994, 0.2010)
        ),
    ])

    # 2. 加载 CIFAR-10 原始测试集
    testset = torchvision.datasets.CIFAR10(
        root='./data',
        train=False,
        download=True,
        transform=transform_test
    )

    # 3. 确定内部使用的攻击模式
    # 如果是为了测试 Clean Label (即测试左上角触发器)，我们需要 'backdoor_topleft' 模式
    # 该模式会给所有样本加左上角触发器，并强制改标为 target，以便 test() 函数计算 Accuracy (即 ASR)
    attack_mode = ATTACK_BACKDOOR
    trigger_desc = "右下角 (标准后门)"
    
    if trigger_type == ATTACK_CLEAN_LABEL:
        attack_mode = ATTACK_BACKDOOR_TL
        trigger_desc = "左上角 (Clean Label)"

    # 4. 包装为 PoisonedDataset
    # 注意: 这里 poison_rate=1.0 意味着测试集里 100% 的样本都带触发器
    all_indices = list(range(len(testset)))
    backdoor_testset = PoisonedDataset(
        dataset=testset,
        indices=all_indices,
        attack_type=attack_mode,
        poison_rate=1.0, 
        target_label=target_label,
        verbose=False  # 静默模式，不打印 Banner
    )

    # 5. 创建 DataLoader
    testloader = DataLoader(
        backdoor_testset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers
    )

    print(f"📊 已创建 ASR 测试集: 触发器={trigger_desc} | 样本数={len(backdoor_testset)}")
    
    return testloader
