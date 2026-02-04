import flwr as fl
import torch
import torch.optim as optim
import torch.nn as nn
from model import get_resnet18
from dataset import load_data, create_backdoor_test_loader, CIFAR10_CLASSES
import sys
import os

# ==================== 初始化设置 ====================
# 获取客户端 ID（优先级：环境变量 > 命令行参数 > 默认值）
# 用法1: CLIENT_ID=2 python client.py  (通过环境变量)
# 用法2: python client.py 0  (通过命令行参数)
CLIENT_ID = None

# 1. 优先从环境变量获取
if 'CLIENT_ID' in os.environ:
    try:
        CLIENT_ID = int(os.environ['CLIENT_ID'])
        print(f"✅ 从环境变量获取 CLIENT_ID={CLIENT_ID}")
    except ValueError:
        print(f"⚠️  环境变量 CLIENT_ID 格式错误: {os.environ['CLIENT_ID']}")

# 2. 其次从命令行参数获取
if CLIENT_ID is None and len(sys.argv) > 1:
    try:
        CLIENT_ID = int(sys.argv[1])
        print(f"✅ 从命令行参数获取 CLIENT_ID={CLIENT_ID}")
    except ValueError:
        print(f"⚠️  命令行参数格式错误: {sys.argv[1]}")

# 3. 最后使用默认值
if CLIENT_ID is None:
    CLIENT_ID = 0
    print("⚠️  未提供客户端 ID，默认使用 ID=0")

# ==================== 获取客户端总数 ====================
# 获取客户端总数（优先级：环境变量 > 默认值）
TOTAL_CLIENTS = None

# 从环境变量获取
if 'TOTAL_CLIENTS' in os.environ:
    try:
        TOTAL_CLIENTS = int(os.environ['TOTAL_CLIENTS'])
        print(f"✅ 从环境变量获取 TOTAL_CLIENTS={TOTAL_CLIENTS}")
    except ValueError:
        print(f"⚠️  环境变量 TOTAL_CLIENTS 格式错误: {os.environ['TOTAL_CLIENTS']}")

# 使用默认值
if TOTAL_CLIENTS is None:
    TOTAL_CLIENTS = 2
    print(f"⚠️  未提供客户端总数，默认使用 TOTAL_CLIENTS=2")

# ==================== 获取攻击配置 ====================
# 攻击类型: None(正常), 'flip'(标签翻转), 'backdoor'(后门)
ATTACK_TYPE = None
if 'ATTACK_TYPE' in os.environ:
    attack_val = os.environ['ATTACK_TYPE'].lower()
    if attack_val in ['flip', 'backdoor']:
        ATTACK_TYPE = attack_val
        print(f"⚠️  攻击模式已启用: {ATTACK_TYPE.upper()}")
    elif attack_val not in ['none', '']:
        print(f"⚠️  未知攻击类型: {attack_val}，使用正常模式")

# 投毒比例 (0.0 ~ 1.0)
# 标签翻转推荐: 0.4 (40%)
# 后门攻击推荐: 0.2 (20%)
POISON_RATE = 0.0
if 'POISON_RATE' in os.environ:
    try:
        POISON_RATE = float(os.environ['POISON_RATE'])
        POISON_RATE = max(0.0, min(1.0, POISON_RATE))  # 限制在 [0, 1] 范围
        print(f"✅ 投毒比例: {POISON_RATE * 100:.1f}%")
    except ValueError:
        print(f"⚠️  POISON_RATE 格式错误: {os.environ['POISON_RATE']}")

# 后门攻击目标标签 (默认为0-飞机)
TARGET_LABEL = 0
if 'TARGET_LABEL' in os.environ:
    try:
        TARGET_LABEL = int(os.environ['TARGET_LABEL'])
        TARGET_LABEL = max(0, min(9, TARGET_LABEL))  # 限制在 [0, 9] 范围
        print(f"✅ 后门目标标签: {TARGET_LABEL}")
    except ValueError:
        print(f"⚠️  TARGET_LABEL 格式错误: {os.environ['TARGET_LABEL']}")

# 自动检测并使用 GPU（如果可用）
DEVICE = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
device_name = "🎮 GPU" if torch.cuda.is_available() else "💻 CPU"

print("\n" + "=" * 50)
print(f"🤖 客户端 {CLIENT_ID} 启动成功")
print(f"👥 客户端总数: {TOTAL_CLIENTS}")
print(f"⚙️  运行设备: {device_name}")
print("=" * 50 + "\n")

# 加载模型和数据
net = get_resnet18().to(DEVICE)
trainloader, testloader = load_data(
    client_id=CLIENT_ID, 
    total_clients=TOTAL_CLIENTS,
    attack_type=ATTACK_TYPE,
    poison_rate=POISON_RATE,
    target_label=TARGET_LABEL
)

# 创建后门测试集（用于评估 ASR - Attack Success Rate）
# 无论客户端是否是攻击者，都创建这个测试集用于统一评估
backdoor_testloader = create_backdoor_test_loader(
    batch_size=64,
    num_workers=0,
    target_label=TARGET_LABEL
)

print(f"📦 数据加载完成: 训练集 {len(trainloader.dataset)} 张图片")
print(f"📦 后门测试集已创建: {len(backdoor_testloader.dataset)} 张带触发器的图片\n")


# ==================== 核心功能函数 ====================

def test(net, testloader):
    """
    模型评估函数：在测试集上评估模型性能

    参数:
        net: 神经网络模型
        testloader: 测试数据加载器

    返回:
        (loss, accuracy): 平均损失和准确率

    工作流程:
        1. 切换到评估模式（关闭 Dropout 和 BatchNorm 的训练行为）
        2. 关闭梯度计算（节省内存，加速推理）
        3. 遍历测试集，统计预测正确的样本数
        4. 计算平均损失和准确率
    """
    criterion = nn.CrossEntropyLoss()
    correct, total, loss = 0, 0, 0.0

    # 清理 GPU 缓存，避免内存碎片
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    net.eval()  # 评估模式
    with torch.no_grad():  # 不计算梯度
        for images, labels in testloader:
            images, labels = images.to(DEVICE), labels.to(DEVICE)
            outputs = net(images)
            loss += criterion(outputs, labels).item()
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

    return loss / len(testloader.dataset), correct / total


def train(net, trainloader, epochs):
    """
    模型训练函数：在本地数据上训练模型

    参数:
        net: 神经网络模型
        trainloader: 训练数据加载器
        epochs: 训练轮数

    工作流程:
        1. 定义损失函数（交叉熵）和优化器（SGD + 动量）
        2. 切换到训练模式（启用 Dropout 和 BatchNorm 的训练行为）
        3. 遍历数据集进行前向传播、反向传播和参数更新

    优化器说明:
        - SGD + Momentum: ResNet 的标准配置，收敛稳定
        - 学习率 0.01: 适合 CIFAR-10 的初始学习率
        - Weight Decay 5e-4: L2 正则化，防止过拟合
    """
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.SGD(net.parameters(), lr=0.01, momentum=0.9, weight_decay=5e-4)

    # 清理 GPU 缓存，避免内存碎片
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    net.train()  # 训练模式
    for epoch in range(epochs):
        running_loss = 0.0
        for batch_idx, (images, labels) in enumerate(trainloader):
            images, labels = images.to(DEVICE), labels.to(DEVICE)

            # 标准训练步骤
            optimizer.zero_grad()           # 清空梯度
            loss = criterion(net(images), labels)  # 前向传播 + 计算损失
            loss.backward()                 # 反向传播
            optimizer.step()                # 更新参数
            running_loss += loss.item()

        # 打印每个 epoch 的平均损失
        avg_loss = running_loss / len(trainloader)
        print(f"      📈 Epoch {epoch+1}/{epochs} - 平均损失: {avg_loss:.4f}")


# ==================== Flower 客户端类 ====================

class MyClient(fl.client.NumPyClient):
    """
    联邦学习客户端类

    继承自 NumPyClient，实现三个核心方法：
    1. get_parameters: 获取模型参数
    2. fit: 接收全局模型，本地训练，返回更新后的参数
    3. evaluate: 评估模型性能
    """

    def get_parameters(self, config):
        """
        获取当前模型的参数（转换为 NumPy 数组）

        返回:
            模型参数列表，每个参数都是 NumPy 数组
        """
        return [val.cpu().numpy() for _, val in net.state_dict().items()]

    def fit(self, parameters, config):
        """
        本地训练流程

        参数:
            parameters: 服务器发来的全局模型参数
            config: 配置信息（包含当前轮次等）

        返回:
            (更新后的参数, 训练样本数, 空字典)
        """
        # 1. 接收服务端发来的配置信息
        current_round = config.get("current_round", "未知")
        print(f"\n{'='*50}")
        print(f"🔄 客户端 {CLIENT_ID} | 第 {current_round} 轮训练开始")
        print(f"{'='*50}")

        # 2. 加载全局参数（用服务器的参数覆盖本地模型，确保在正确的设备上）
        params_dict = zip(net.state_dict().keys(), parameters)
        state_dict = {k: torch.tensor(v).to(DEVICE) for k, v in params_dict}
        net.load_state_dict(state_dict, strict=True)
        print("    ✅ 已加载全局模型参数")

        # 3. 执行本地训练
        print("    🏋️  开始本地训练...")
        train(net, trainloader, epochs=1)
        print(f"    ✅ 本地训练完成\n")

        # 4. 返回更新后的参数给服务器
        return self.get_parameters(config={}), len(trainloader.dataset), {}

    def evaluate(self, parameters, config):
        """
        模型评估流程 - 同时评估正常准确率和后门攻击成功率 (ASR)

        参数:
            parameters: 服务器发来的模型参数
            config: 配置信息

        返回:
            (损失值, 测试样本数, 指标字典)
            指标字典包含:
                - accuracy: 正常测试集准确率 (Main Task Accuracy)
                - asr: 后门攻击成功率 (Attack Success Rate)
        """
        # 1. 加载参数（确保参数在正确的设备上）
        params_dict = zip(net.state_dict().keys(), parameters)
        state_dict = {k: torch.tensor(v).to(DEVICE) for k, v in params_dict}
        net.load_state_dict(state_dict, strict=True)

        # 2. 评估正常测试集准确率 (Main Task Accuracy)
        # 这是模型在干净数据上的表现，应该维持在较高水平
        loss, accuracy = test(net, testloader)
        
        # 3. 评估后门攻击成功率 (ASR - Attack Success Rate)
        # 给模型看全是带触发器的图片，看模型是否将它们都识别为目标标签
        # ASR 高 = 后门攻击成功，模型被植入了后门
        # ASR 低 = 后门攻击失败或被防御住了
        _, asr = test(net, backdoor_testloader)
        
        # 4. 打印评估结果
        print(f"\n    {'='*45}")
        print(f"    📊 客户端 {CLIENT_ID} 评估报告")
        print(f"    {'='*45}")
        print(f"    ✅ 正常准确率 (MTA): {accuracy * 100:.2f}%")
        print(f"    💀 后门成功率 (ASR): {asr * 100:.2f}%")
        print(f"       (目标标签: {TARGET_LABEL} - {CIFAR10_CLASSES[TARGET_LABEL]})")
        print(f"    {'='*45}\n")
        
        # 结果解读:
        # - MTA 高 + ASR 低: 模型健康，没有后门
        # - MTA 高 + ASR 高: 后门攻击成功！模型被植入了隐蔽后门
        # - MTA 低 + ASR 低: 标签翻转攻击可能生效，模型性能下降
        # - MTA 低 + ASR 高: 攻击太激进，失去隐蔽性

        # 5. 返回结果给服务器
        return float(loss), len(testloader.dataset), {
            "accuracy": float(accuracy),
            "asr": float(asr)
        }


# ==================== 启动客户端 ====================
print("🔗 正在连接服务器 127.0.0.1:8080...\n")
fl.client.start_numpy_client(server_address="127.0.0.1:8080", client=MyClient())