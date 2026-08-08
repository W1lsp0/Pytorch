"""
==============================================================================
🌍 Flower Server 联邦学习服务端 (Entry Point)
==============================================================================
这是 Flower 联邦学习的中央服务器入口。

主要职责:
  1. 配置聚合策略 (TMAA_FedAvg)
  2. 启动 Flower Server
  3. 协调训练流程

配置:
  - 算法: FedAvg
  - 轮次: 20
  - 最小客户端数: 10

作者: Flwr 联邦学习项目
Refactored: 2026-02-11
==============================================================================
"""

import flwr as fl
from typing import List, Tuple
from flwr.common import Metrics
import sys

# 导入模块化组件
from strategy import TMAA_FedAvg

# ==================== 训练配置 ====================
NUM_ROUNDS = 30
EVAL_BATCH_SIZE = 64

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Subset
import torchvision
import torchvision.transforms as transforms

# ==================== (SCHEME D) 预加载服务器端纯净验证集 ====================
print("📥 [Server] 正在从本地或者网络拉取 CIFAR-10 防御级纯净验证集...", flush=True)

transform_test = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
])

testset = torchvision.datasets.CIFAR10(
    root='./data', train=False, download=True, transform=transform_test
)

# ==================== (SCHEME D) 预加载服务器端绝对平衡验证集 ====================
# 这里不仅抽取 500 张，更是要保证 0-9 每一个类别精确抽取 50 张！
proxy_indices = []
class_counts = {i: 0 for i in range(10)}

if hasattr(testset, 'targets'):
    targets = testset.targets
else:
    # 针对部分老版本属性兼容
    targets = [y for _, y in testset]

for idx, label in enumerate(targets):
    if class_counts[label] < 50:
        proxy_indices.append(idx)
        class_counts[label] += 1
    # 当 10 个类目各凑齐 50 个时停止搜寻
    if all(count == 50 for count in class_counts.values()):
        break

clean_proxy_testset = Subset(testset, proxy_indices)

# 创建 DataLoader 以备后续进行前向推理
proxy_testloader = DataLoader(
    clean_proxy_testset, 
    batch_size=EVAL_BATCH_SIZE, 
    shuffle=False, 
    num_workers=2, 
    pin_memory=True
)
print(f"✅ [Server] 纯净验证集挂载完毕! 样本数量: {len(proxy_testloader.dataset)}", flush=True)

# ==================== (SCHEME G) 预加载对抗探针验证集 (Noisy Probes) ====================
print("📥 [Server] 正在构建 Scheme G 主动探针数据集 (Noisy Probes)...", flush=True)

# 我们增加一个自定义的 Transform，用于在图片上叠加强烈的空间噪声，破坏自然流形
class AddGaussianNoise(object):
    def __init__(self, mean=0., std=1.5):
        self.std = std
        self.mean = mean
        
    def __call__(self, tensor):
        return tensor + torch.randn(tensor.size()) * self.std + self.mean

transform_noisy_probe = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
    AddGaussianNoise(0., 2.0) # 施加极强的局部高斯噪声以触发异常神经元
])

# 重新加载相同 500 张图片的 Subset，但是带上受损的 transform
noisy_testset = torchvision.datasets.CIFAR10(
    root='./data', train=False, download=False, transform=transform_noisy_probe
)
noisy_proxy_testset = Subset(noisy_testset, proxy_indices)

noisy_probe_loader = DataLoader(
    noisy_proxy_testset, 
    batch_size=EVAL_BATCH_SIZE, 
    shuffle=False, 
    num_workers=2, 
    pin_memory=True
)
print(f"✅ [Server] 探针验证集(Noisy Probes)构建完毕! 激进噪声比: std=2.0", flush=True)

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Client'))
try:
    from model import get_resnet18
except ImportError as e:
    raise ImportError(
        f"无法导入 get_resnet18: {e}。请确保 Client/model.py 位于正确路径。"
    ) from e

# 借用 Client 端一模一样的 ResNet-18 结构以匹配 [64,3,3,3] 的 conv1_weight
base_net = get_resnet18()
base_net.fc = nn.Linear(base_net.fc.in_features, 10)  # CIFAR-10 是 10 分类
# ==================================================================================

# ==================== 解决 Windows 中文乱码问题 ====================
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
# ================================================================

# ==================== 配置回调函数 ====================
def get_on_fit_config_fn(server_round: int):
    """
    配置函数：向客户端下发当前训练轮次信息
    客户端可以在 fit() 的 config 参数中读取到。
    """
    return {
        "current_round": server_round,
        "global_batch_size": 32, # 示例配置
    }


# ==================== 聚合回调函数 ====================
def weighted_average(metrics: List[Tuple[int, Metrics]]) -> Metrics:
    """
    聚合函数：处理客户端返回的 metrics
    
    计算:
        - 全局样本加权平均准确率 (Accuracy)
        - 全局样本加权平均后门成功率 (ASR)
        
    Args:
        metrics: list of (num_examples, metrics_dict)
    """
    total_examples = sum([num_examples for num_examples, _ in metrics])
    
    # 聚合 Accuracy
    weighted_accuracies = [num * m["accuracy"] for num, m in metrics]
    aggregated_accuracy = sum(weighted_accuracies) / total_examples

    # 聚合 ASR (如果存在)
    # 注意: 部分客户端可能没传这个字段，需要 safe get
    weighted_asrs = [num * m.get("asr", 0.0) for num, m in metrics]
    aggregated_asr = sum(weighted_asrs) / total_examples

    # 美化输出：显示全局指标
    # 原子输出 (防止多线程交错)
    print("\n".join([
        "",
        "╔" + "═"*58 + "╗",
        "║  📊 全局模型评估结果 (Global Metrics)".ljust(60) + "║",
        "╠" + "═"*58 + "╣",
        f"║  🌟 平均准确率 (Accuracy):   {aggregated_accuracy * 100:.2f}%{' '*24}║",
        f"║  💀 平均攻击率 (ASR):        {aggregated_asr * 100:.2f}%{' '*24}║",
        "╚" + "═"*58 + "╝",
        ""
    ]))

    return {
        "accuracy": aggregated_accuracy,
        "asr": aggregated_asr
    }

# ==================== 策略配置 ====================
# 使用 TMAA 自定义策略
strategy = TMAA_FedAvg(
    fraction_fit=1.0,                      # 每轮采样 100% 的可用客户端参与训练
    fraction_evaluate=1.0,                 # 每轮采样 100% 的可用客户端参与评估
    min_fit_clients=20,                     # 每轮至少请求 20 个客户端
    min_evaluate_clients=20,                # 每轮至少请求 20 个客户端
    min_available_clients=20,               # 启动训练前等待至少 20 个客户端连接
    
    evaluate_metrics_aggregation_fn=weighted_average,  # 配置聚合函数
    on_fit_config_fn=get_on_fit_config_fn,            # 配置下发函数
    
    # [Scheme D] 注入服务器验证代理所需的神器
    proxy_net=base_net,
    proxy_testloader=proxy_testloader,
    
    # [Scheme G] 注入探测用的受损探测集
    noisy_probe_loader=noisy_probe_loader
)


# ==================== 启动服务器 ====================
def main(server_address="0.0.0.0:8080"):
    # 原子输出 (防止多线程交错)
    print("\n".join([
        "",
        "╔" + "═"*60 + "╗",
        f"║  🚀 联邦学习服务器启动中... {' '*33}║",
        "╠" + "═"*60 + "╣",
        f"║  📦 模型架构: ResNet-18{' '*38}║",
        f"║  📊 数据集:   CIFAR-10{' '*38}║",
        f"║  🔗 监听地址: {server_address.ljust(18)}{' '*28}║",
        f"║  🔄 训练轮次: {NUM_ROUNDS} Rounds{' '*38}║",
        "╚" + "═"*60 + "╝",
        ""
    ]))

    # 启动 Flower 服务器 (阻塞运行)
    fl.server.start_server(
        server_address=server_address,
        config=fl.server.ServerConfig(num_rounds=NUM_ROUNDS),
        strategy=strategy
    )

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Flower Server")
    parser.add_argument("--server_address", type=str, default="0.0.0.0:8080", help="Server address.")
    args = parser.parse_args()
    main(args.server_address)
