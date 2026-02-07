
"""
==============================================================================
🚀 Demo Client: TMAA 数据上报演示客户端
==============================================================================
本脚本演示如何启动一个联邦学习客户端，并利用 TMAA 架构打包上传：
1. 静态设备画像 (Device Profile)
2. 动态硬件遥测 (Telemetry from DB)
3. 训练元数据 (Metadata)
4. TEE 数字签名 (Digital Signature)

无需真实 GPU 训练，主要演示数据流与安全协议。
"""

import flwr as fl
import time
import json
import os
import argparse
import random
import numpy as np
import torch # Added torch for real execution

# 导入 TMAA 模块
from tmaa.tee_sim import SimulatedTEE
from tmaa.sidecar import TMAA_Sidecar

# 模拟的设备ID (必须在数据库中存在)
DEFAULT_DEVICE_ID = "worker_0000"

# 导入真实数据加载模块
from dataset import load_data

class DemoClient(fl.client.NumPyClient):
    def __init__(self, device_id: str):
        self.device_id = device_id
        
        # 1. 初始化 TEE (身份认证)
        print(f"🔐 [Init] 初始化模拟 TEE (Device: {self.device_id})...")
        self.tee = SimulatedTEE(device_id=self.device_id)
        
        # 2. 启动 Sidecar (启用数据库仿真模式)
        print(f"🛡️  [Init] 启动 TMAA Sidecar (Simulation Mode)...")
        self.agent = TMAA_Sidecar(self.tee, pid=os.getpid(), use_simulation=True)
        
    def fit(self, parameters, config):
        """
        执行真实的数据加载与训练循环
        """
        round_num = config.get("current_round", 1)
        print(f"\n" + "="*50)
        print(f"🔄 Round {round_num} | 收到服务器训练指令")
        print("="*50)
        
        # [Step 1] 从数据库读取设备画像，决定行为
        db = self.agent.monitor.db_manager # 复用 sidecar 的 db 连接
        profile = db.get_device_info(self.device_id)
        if not profile:
            print(f"❌ 数据库中未找到 ID: {self.device_id}，请先运行生成脚本。")
            return [], 0, {}
            
        attack_type = profile.get("attack_type", "none")
        is_malicious = profile.get("is_malicious", False)
        
        print(f"\n🔍 [DB Check] 设备身份: {self.device_id}")
        print(f"   - 角色: {'😈 Malicious' if is_malicious else '✅ Honest'}")
        print(f"   - 策略: {attack_type.upper()}")
        
        # [Step 2] 加载真实数据 (应用投毒)
        print(f"\n📚 [Data] 加载本地数据集 (Mode: {attack_type})...")
        # 提取 ID 数字 (worker_0005 -> 5)
        cid = int(self.device_id.split("_")[-1]) if "_" in self.device_id else 0
        
        trainloader, _ = load_data(
            client_id=cid, 
            total_clients=100, # 假设100个客户端
            attack_type=attack_type if attack_type != 'none' else None,
            poison_rate=0.5,   # 如果攻击，注入50%毒药
            target_label=0
        )
        
        # [Step 3] 开启监控
        print("🛡️  [TMAA] 开启硬件行为监控...")
        self.agent.start_monitoring()
        
        # [Step 4] 执行真实训练循环 (Iterate DataLoader)
        # 为演示速度，仅运行 1 个 Epoch 的前 20 个 Batch
        print(f"🏋️  执行本地计算 (Real Execution)...")
        sample_count = len(trainloader.dataset)
        
        running_loss = 0.0
        for i, (images, labels) in enumerate(trainloader):
            if i >= 20: break # Demo Limit
            # 模拟计算消耗
            _ = torch.mean(images) 
            time.sleep(0.05) 
            if i % 5 == 0:
                print(f"    Batch {i}/20 | Data Shape: {images.shape}")
                
        # [Step 5] 停止监控 & 生成报告
        print("🛡️  [TMAA] 停止监控，生成可信报告...")
        self.agent.stop_monitoring()
        
        # 构造元数据
        meta = {
            "round": round_num,
            "samples": sample_count,
            "attack_mode": attack_type
        }
        
        # 生成签名报告
        trust_pkg = self.agent.generate_trust_report(meta)
        
        print("\n📦 [Upload] 数据包准备就绪:")
        print(f"   - Signature: {trust_pkg['signature'][:20]}...")
        fingerprint = trust_pkg['trust_report']['metrics']['behavior_fingerprint']
        print(f"   - Fingerprint: {fingerprint}")

        metrics = {"trust_report_json": json.dumps(trust_pkg)}
        return [], sample_count, metrics

    def evaluate(self, parameters, config):
        return 0.5, 1000, {"accuracy": 0.8}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", type=str, default=DEFAULT_DEVICE_ID, help="Simulated Device ID (must exist in DB)")
    parser.add_argument("--server", type=str, default="127.0.0.1:8080", help="Server Address")
    parser.add_argument("--test", action="store_true", help="Run in standalone test mode (no server connection)")
    args = parser.parse_args()
    
    print(f"🚀 启动演示客户端 (ID: {args.device})")
    
    if args.test:
        print("\n🧪 [Test Mode] 运行本地模拟训练与打包流程...")
        client = DemoClient(args.device)
        # 模拟一次 fit 调用
        config = {"current_round": 1}
        client.fit(parameters=[], config=config)
        print("\n✅ 测试模式执行完毕。")
        return

    # 启动 Client
    try:
        fl.client.start_numpy_client(
            server_address=args.server,
            client=DemoClient(args.device)
        )
    except Exception as e:
        print(f"\n❌ 连接服务器失败: {e}")
        print("💡 提示: 请确保先启动 Flower Server (python server.py)")

if __name__ == "__main__":
    main()
