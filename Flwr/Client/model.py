import torch
import torch.nn as nn
import torchvision.models as models


def get_resnet18(num_classes: int = 10) -> nn.Module:
    """
    构建适用于 CIFAR-10 的 ResNet-18 模型。

    Args:
        num_classes: 分类类别数，默认为 10（CIFAR-10）

    Returns:
        修改后的 ResNet-18 模型
    """
    # 1. 加载标准 ResNet18结构
    # weights=None 表示我们需要从头开始训练，不使用预训练权重
    net = models.resnet18(weights=None)

    # ==================== 关键修改 ====================
    # 标准 ResNet 第一层是针对 ImageNet (224x224) 设计的：
    # - 原始配置：7x7 卷积核，stride=2，然后接 MaxPool
    # - 问题：CIFAR-10 图片只有 32x32，会导致特征图过小，丢失信息
    #
    # 解决方案：
    # - 将 conv1 改为 3x3 小卷积核，stride=1（保持分辨率）
    # - 去掉 MaxPool 层（避免进一步缩小特征图）
    net.conv1 = nn.Conv2d(3, 64, kernel_size=3, stride=1, padding=1, bias=False)
    net.maxpool = nn.Identity()  # Identity 层：直通，不做任何操作

    # ==================== 修改输出层 ====================
    # 将最后的全连接层改为 10 类输出（CIFAR-10 有 10 个类别）
    # 原始 ResNet-18 的 fc 层输出 1000 类（ImageNet）
    net.fc = nn.Linear(net.fc.in_features, num_classes)

    return net