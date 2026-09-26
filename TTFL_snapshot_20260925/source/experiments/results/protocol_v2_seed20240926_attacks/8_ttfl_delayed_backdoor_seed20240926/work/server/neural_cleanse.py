# -*- coding: utf-8 -*-
"""
==============================================================================
🔬 Neural Cleanse — 触发器逆向工程检测模块
==============================================================================
职责：
    对客户端提交的模型进行"CT 扫描"：通过反向优化，尝试为每个目标类别
    找到一个面积尽可能小的"贴纸"（Mask + Pattern），使得贴上后所有输入
    都被分类为该类别。如果某个类别的最小贴纸面积异常小，则说明模型中
    存在后门触发器。

    核心算法来自论文:
    Wang et al., "Neural Cleanse: Identifying and Mitigating Backdoor Attacks
    in Neural Networks", IEEE S&P 2019.

作者: Flwr 联邦学习项目组
==============================================================================
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import copy
from typing import Tuple, List, Optional


def reverse_engineer_trigger(
    model: nn.Module,
    clean_loader: torch.utils.data.DataLoader,
    target_class: int,
    device: torch.device,
    num_steps: int = 50,
    lr: float = 0.05,
    lambda_l1: float = 0.01,
    num_batches: int = 2,
) -> float:
    """
    对单个目标类别执行触发器逆向优化。

    尝试找到一个最小的 (Mask, Pattern) 使得：
        f(x * (1 - M) + Delta * M) == target_class   对所有 x 成立

    参数:
        model: 待检测的神经网络模型（已加载权重，eval 模式）
        clean_loader: Server 端的纯净验证集
        target_class: 当前尝试逆向的目标类别 (0~9)
        device: 计算设备
        num_steps: 优化迭代步数
        lr: 学习率
        lambda_l1: L1 正则化系数（鼓励掩码尽可能小）
        num_batches: 每步使用的 batch 数量

    返回:
        mask_l1_norm: 最终优化出的掩码的 L1 范数（面积指标）
    """
    model.eval()

    # 初始化可学习掩码和图案
    # mask 使用 sigmoid 映射到 [0, 1]，pattern 使用 tanh 映射到 [-1, 1]
    mask_raw = torch.zeros(1, 1, 32, 32, device=device, requires_grad=True)
    pattern_raw = torch.zeros(1, 3, 32, 32, device=device, requires_grad=True)

    optimizer = torch.optim.Adam([mask_raw, pattern_raw], lr=lr)

    # 预加载 clean batches（避免每步重新遍历 DataLoader）
    clean_batches = []
    for i, (images, labels) in enumerate(clean_loader):
        if i >= num_batches:
            break
        clean_batches.append(images.to(device))

    if not clean_batches:
        return 1e6  # 安全回退

    for step in range(num_steps):
        total_loss = 0.0
        optimizer.zero_grad()

        mask = torch.sigmoid(mask_raw)    # [0, 1]
        pattern = torch.tanh(pattern_raw) # [-1, 1]

        for images in clean_batches:
            batch_size = images.size(0)
            target_labels = torch.full(
                (batch_size,), target_class, device=device, dtype=torch.long
            )

            # 将 mask 和 pattern 应用到干净图片上
            poisoned = images * (1 - mask) + pattern * mask
            outputs = model(poisoned)

            # 分类损失：让所有图片都被分类为 target_class
            ce_loss = F.cross_entropy(outputs, target_labels)
            # L1 正则化：鼓励掩码面积尽可能小
            l1_loss = lambda_l1 * torch.sum(torch.abs(mask))

            loss = ce_loss + l1_loss
            total_loss += loss

        total_loss.backward()
        optimizer.step()

    # 计算最终掩码的 L1 范数（总面积）
    with torch.no_grad():
        final_mask = torch.sigmoid(mask_raw)
        mask_l1 = torch.sum(torch.abs(final_mask)).item()

    return mask_l1


def neural_cleanse_scan(
    model: nn.Module,
    clean_loader: torch.utils.data.DataLoader,
    device: torch.device,
    num_classes: int = 10,
    num_steps: int = 50,
    lr: float = 0.05,
    lambda_l1: float = 0.01,
    num_batches: int = 2,
) -> Tuple[float, int, List[float]]:
    """
    对一个模型执行全类别 Neural Cleanse 扫描。

    参数:
        model: 待扫描的模型
        clean_loader: 纯净验证集
        device: 计算设备
        num_classes: 类别数量（CIFAR-10 = 10）
        num_steps: 每个类别的优化步数
        lr: 优化学习率
        lambda_l1: L1 正则化权重
        num_batches: 每步使用的 batch 数量

    返回:
        (anomaly_index, suspect_class, mask_norms)
        - anomaly_index: MAD 离群点指数，越高越可疑（> 2.0 基本确认后门）
        - suspect_class: 最可疑的目标类别
        - mask_norms: 各类别的掩码 L1 范数列表
    """
    mask_norms = []

    for target in range(num_classes):
        norm = reverse_engineer_trigger(
            model=model,
            clean_loader=clean_loader,
            target_class=target,
            device=device,
            num_steps=num_steps,
            lr=lr,
            lambda_l1=lambda_l1,
            num_batches=num_batches,
        )
        mask_norms.append(norm)

    mask_norms_arr = np.array(mask_norms)

    # MAD (Median Absolute Deviation) 离群点检测
    # 后门类别的 mask_norm 会异常小（面积极小的贴纸就能劫持分类）
    median = np.median(mask_norms_arr)
    mad = np.median(np.abs(mask_norms_arr - median))

    if mad < 1e-6:
        mad = 1e-6

    # anomaly_index: 负方向离群度（norm 越小于中位数，index 越高）
    anomaly_indices = (median - mask_norms_arr) / (1.4826 * mad)

    max_anomaly = float(np.max(anomaly_indices))
    suspect_class = int(np.argmax(anomaly_indices))

    return max_anomaly, suspect_class, mask_norms


def scan_client_model(
    proxy_net: nn.Module,
    client_weights: list,
    clean_loader: torch.utils.data.DataLoader,
    device: torch.device,
    num_classes: int = 10,
    num_steps: int = 50,
    num_batches: int = 2,
) -> Tuple[float, int, List[float]]:
    """
    便捷接口：加载客户端权重到代理网络后执行 NC 扫描。

    参数:
        proxy_net: Server 端的代理网络架构（用于 deepcopy）
        client_weights: 客户端权重列表（numpy arrays）
        clean_loader: 纯净验证集
        device: 计算设备
        num_classes: 类别数
        num_steps: 优化步数
        num_batches: 每步 batch 数

    返回:
        (anomaly_index, suspect_class, mask_norms)
    """
    # 构建临时模型副本
    temp_net = copy.deepcopy(proxy_net).to(device)
    params_dict = zip(temp_net.state_dict().keys(), client_weights)
    state_dict = {k: torch.tensor(v) for k, v in params_dict}
    temp_net.load_state_dict(state_dict, strict=True)
    temp_net.eval()

    # 执行扫描
    anomaly_index, suspect_class, mask_norms = neural_cleanse_scan(
        model=temp_net,
        clean_loader=clean_loader,
        device=device,
        num_classes=num_classes,
        num_steps=num_steps,
        num_batches=num_batches,
    )

    # 清理显存
    del temp_net
    del state_dict
    torch.cuda.empty_cache()

    return anomaly_index, suspect_class, mask_norms
