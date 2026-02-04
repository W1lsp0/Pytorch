import flwr as fl
from typing import List, Tuple
from flwr.common import Metrics


# ==================== 配置函数 ====================
def get_on_fit_config_fn(server_round: int):
    """
    配置函数：向客户端下发当前训练轮次信息

    参数:
        server_round: 当前是第几轮训练

    返回:
        包含轮次信息的字典，会被发送给所有客户端
    """
    return {"current_round": server_round}


# ==================== 聚合函数 ====================
def weighted_average(metrics: List[Tuple[int, Metrics]]) -> Metrics:
    """
    聚合函数：计算所有客户端的加权平均准确率

    参数:
        metrics: 列表，每个元素是 (样本数, 指标字典)
                例如: [(5000, {"accuracy": 0.75}), (5000, {"accuracy": 0.80})]

    返回:
        包含全局准确率的字典

    工作原理:
        - 每个客户端的准确率按其数据量加权
        - 数据多的客户端对全局准确率影响更大
        - 公式: 全局准确率 = Σ(样本数 × 准确率) / Σ(样本数)
    """
    # 计算加权准确率：每个客户端的准确率 × 该客户端的样本数
    accuracies = [num_examples * m["accuracy"] for num_examples, m in metrics]
    # 统计总样本数
    examples = [num_examples for num_examples, _ in metrics]

    # 计算全局加权平均准确率
    aggregated_accuracy = sum(accuracies) / sum(examples)

    # 美化输出：显示全局准确率
    print("\n" + "🌟" * 25)
    print(f"  📊 全局准确率: {aggregated_accuracy * 100:.2f}%")
    print("🌟" * 25 + "\n")

    return {"accuracy": aggregated_accuracy}


# ==================== 联邦学习策略 ====================
# 使用 FedAvg (联邦平均) 算法
strategy = fl.server.strategy.FedAvg(
    fraction_fit=1.0,                      # 每轮使用 100% 的可用客户端
    min_fit_clients=3,                     # 每轮至少需要 3 个客户端参与训练
    min_available_clients=3,               # 启动训练前至少需要 3 个客户端连接
    evaluate_metrics_aggregation_fn=weighted_average,  # 聚合评估指标
    on_fit_config_fn=get_on_fit_config_fn,            # 下发配置信息
)

# ==================== 启动服务器 ====================
print("\n" + "=" * 60)
print("🚀 联邦学习服务器启动中...")
print("📦 模型: ResNet-18")
print("📊 数据集: CIFAR-10")
print("🔗 监听地址: 0.0.0.0:8080")
print("🔄 训练轮次: 20 轮")
print("=" * 60 + "\n")

# 启动 Flower 服务器
fl.server.start_server(
    server_address="0.0.0.0:8080",
    config=fl.server.ServerConfig(num_rounds=20),
    strategy=strategy
)