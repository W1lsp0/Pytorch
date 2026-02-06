"""
==============================================================================
🤖 ResNet-18 模型定义模块
==============================================================================
本模块提供适配 CIFAR-10 数据集的 ResNet-18 模型构建函数。

核心修改说明:
    - 原始 ResNet-18 针对 ImageNet (224x224) 设计
    - CIFAR-10 图像尺寸仅为 32x32，需进行适配
    - 主要修改包括: 调整首层卷积核、移除最大池化层

作者: Flwr 联邦学习项目
==============================================================================
"""

import torch
import torch.nn as nn
import torchvision.models as models


def get_resnet18(num_classes: int = 10) -> nn.Module:
    """
    构建适用于 CIFAR-10 的 ResNet-18 模型。

    本函数对标准 ResNet-18 进行了精心调整，使其能够高效处理
    32x32 的小尺寸图像，同时保持模型的强大表征能力。

    Args:
        num_classes (int): 分类类别数量
            - 默认值: 10 (对应 CIFAR-10 的 10 个类别)
            - 可根据实际任务调整

    Returns:
        nn.Module: 修改后的 ResNet-18 模型实例

    Architecture Modifications:
        ┌─────────────────────────────────────────────────────────────────┐
        │  层级          │  原始 ImageNet 配置    │  CIFAR-10 适配配置    │
        ├─────────────────────────────────────────────────────────────────┤
        │  conv1         │  7×7, stride=2        │  3×3, stride=1       │
        │  maxpool       │  3×3, stride=2        │  Identity (跳过)     │
        │  fc (输出层)   │  1000 类              │  10 类               │
        └─────────────────────────────────────────────────────────────────┘

    Example:
        >>> model = get_resnet18(num_classes=10)
        >>> print(model)

    Note:
        - 使用 weights=None 表示从头开始训练，不加载预训练权重
        - 适用于联邦学习场景下的本地模型初始化
    """

    # ======================== 步骤 1: 加载基础模型 ========================
    # 创建标准 ResNet-18 结构 (无预训练权重)
    net = models.resnet18(weights=None)
    
    print("┌" + "─" * 58 + "┐")
    print("│  🏗️  正在构建 CIFAR-10 适配版 ResNet-18 模型...             │")
    print("└" + "─" * 58 + "┘")

    # ======================== 步骤 2: 适配首层卷积 ========================
    # 
    # 📌 问题分析:
    #   原始 ResNet-18 的第一层使用 7×7 大卷积核配合 stride=2
    #   这种设计会将 32×32 图像快速压缩至 16×16
    #   后续的 MaxPool 会进一步压缩至 8×8，严重丢失空间信息
    #
    # 💡 解决方案:
    #   将首层改为 3×3 小卷积核，stride=1，保持输入分辨率
    #
    net.conv1 = nn.Conv2d(
        in_channels=3,       # RGB 三通道输入
        out_channels=64,     # 输出 64 个特征通道
        kernel_size=3,       # 3×3 小卷积核 (原为 7×7)
        stride=1,            # 步幅为 1 (原为 2)
        padding=1,           # 填充为 1，保持空间尺寸
        bias=False           # 后接 BatchNorm，不需要偏置
    )

    # ======================== 步骤 3: 移除池化层 ==========================
    # 
    # 📌 原因:
    #   MaxPool 层会将特征图尺寸减半
    #   对于 32×32 的小图像，这会导致有效感受野覆盖过大
    #   使用 Identity 层直接跳过，保留更多空间细节
    #
    net.maxpool = nn.Identity()

    # ======================== 步骤 4: 修改输出层 ==========================
    # 
    # 📌 说明:
    #   原始 fc 层输出 1000 类 (ImageNet 类别数)
    #   需要修改为目标数据集的类别数
    #
    in_features = net.fc.in_features  # 获取原始输入维度 (512)
    net.fc = nn.Linear(in_features, num_classes)

    print(f"│  ✅ 模型构建完成! 输出类别数: {num_classes}                        │")
    print("└" + "─" * 58 + "┘\n")

    return net


# ============================ 模块自测试 ================================
if __name__ == "__main__":
    # 创建模型并打印摘要
    model = get_resnet18(num_classes=10)
    
    # 计算模型参数量
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    
    print("\n" + "=" * 60)
    print("📊 模型统计信息")
    print("=" * 60)
    print(f"   总参数量:     {total_params:,}")
    print(f"   可训练参数:   {trainable_params:,}")
    print(f"   模型大小:     ~{total_params * 4 / 1024 / 1024:.2f} MB (FP32)")
    print("=" * 60)