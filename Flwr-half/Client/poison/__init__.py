"""
==============================================================================
☠️ Poison 投毒攻击模块
==============================================================================
本模块提供联邦学习中常见的投毒攻击实现。

包含的攻击类型:
    1. 标签翻转攻击 (Label Flipping)
    2. 后门攻击 (Backdoor Attack)

导出接口:
    - PoisonedDataset: 投毒数据集包装器
    - create_backdoor_test_loader: 后门测试集加载器工厂
    - CIFAR10_CLASSES: CIFAR-10 类别名称列表

作者: Flwr 联邦学习项目
==============================================================================
"""

from .attack_wrapper import (
    PoisonedDataset,
    create_backdoor_test_loader,
    CIFAR10_CLASSES
)

# 模块公开接口
__all__ = [
    'PoisonedDataset',
    'create_backdoor_test_loader',
    'CIFAR10_CLASSES'
]
