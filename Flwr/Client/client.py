# client/client_main.py (这是修改后的 client.py)

import flwr as fl
import torch
import torch.optim as optim
import torch.nn as nn
from model import get_resnet18
from dataset import load_data
import sys
import os
import time

# --- 新增: 导入 TMAA 模块 ---
from tee_sim import SimulatedTEE
from tmaa.sidecar import TMAA_Sidecar

# ... (保留原有的环境变量获取代码 CLIENT_ID, TOTAL_CLIENTS 等) ...
# 为了节省篇幅，这里假设之前的 ENV 读取代码已经存在
# CLIENT_ID, TOTAL_CLIENTS, ATTACK_TYPE ... = ... (Copy from original client.py)
# 这里仅为运行示例写死或简写，请保留你原文件中的这部分逻辑
# -----------------------------------------------------------
CLIENT_ID = int(os.environ.get("CLIENT_ID", 0))
TOTAL_CLIENTS = int(os.environ.get("TOTAL_CLIENTS", 2))
DEVICE = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
# -----------------------------------------------------------

# 加载数据 (全局，方便 Sidecar 访问)
print("📦 Loading Data...")
trainloader, testloader = load_data(
    client_id=CLIENT_ID,
    total_clients=TOTAL_CLIENTS,
    # 传入攻击参数...
)
net = get_resnet18().to(DEVICE)

# --- 新增: 初始化可信硬件与监控代理 ---
print("🔐 Initializing TEE & TMAA...")
tee_hardware = SimulatedTEE(device_id=f"device_{CLIENT_ID}")
tmaa_agent = TMAA_Sidecar(tee_hardware, pid=os.getpid())


def train(net, trainloader, epochs):
    """(保持原有的训练逻辑不变)"""
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.SGD(net.parameters(), lr=0.01, momentum=0.9)
    net.train()
    for epoch in range(epochs):
        for images, labels in trainloader:
            images, labels = images.to(DEVICE), labels.to(DEVICE)
            optimizer.zero_grad()
            loss = criterion(net(images), labels)
            loss.backward()
            optimizer.step()
        # 模拟训练耗时，方便 Observation
        time.sleep(0.1)


class MyClient(fl.client.NumPyClient):
    def get_parameters(self, config):
        return [val.cpu().numpy() for _, val in net.state_dict().items()]

    def fit(self, parameters, config):
        # 1. 加载参数
        params_dict = zip(net.state_dict().keys(), parameters)
        state_dict = {k: torch.tensor(v).to(DEVICE) for k, v in params_dict}
        net.load_state_dict(state_dict, strict=True)

        # ====================== TMAA 介入开始 ======================
        print(f"\n🛡️ [Step 1] TMAA 启动 Sidecar 监控...")
        tmaa_agent.start_monitoring()

        print(f"🛡️ [Step 2] TMAA 执行数据隐私层审计 (L3)...")
        # 可以在训练前进行数据扫描，计算 Non-IID 指标
        tmaa_agent.scan_data(trainloader, net, DEVICE)
        # ==========================================================

        # 3. 执行本地训练 (Worker)
        start_time = time.time()
        print("🏋️  开始本地训练...")
        train(net, trainloader, epochs=1)
        duration = time.time() - start_time
        print("✅ 本地训练完成")

        # ====================== TMAA 介入结束 ======================
        print(f"🛡️ [Step 3] TMAA 停止监控并生成报告...")
        tmaa_agent.stop_monitoring()

        # 收集训练元数据 (Worker 主动上报的部分)
        meta_data = {
            "duration": round(duration, 2),
            "epochs": 1,
            "sample_count": len(trainloader.dataset)
        }

        # 生成最终的可信报告 (包含签名)
        trust_package = tmaa_agent.generate_trust_report(meta_data)
        # ==========================================================

        # 4. 返回结果 (注意：TrustReport 放在 metrics 字典中传回服务器)
        # Flower 的 fit 返回: (parameters, num_examples, metrics)
        # 我们把 trust_package 塞进 metrics

        # 注意: Flower 传输 metrics 默认可能只支持简单类型，复杂 JSON 可能需要序列化为字符串
        import json
        metrics_payload = {
            "trust_report_json": json.dumps(trust_package)
        }

        return self.get_parameters(config={}), len(trainloader.dataset), metrics_payload

    def evaluate(self, parameters, config):
        # (保持原有的评估逻辑)
        # ... 这里省略，保持你原来的 helper.test 调用 ...
        return 0.0, 10, {"accuracy": 0.0}

    # 启动客户端


if __name__ == "__main__":
    fl.client.start_numpy_client(server_address="127.0.0.1:8080", client=MyClient())