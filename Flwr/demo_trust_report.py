
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
import time
import json
import os

# Import TMAA modules
from Client.tmaa.sidecar import TMAA_Sidecar
from Client.tmaa.tee_sim import SimulatedTEE

# ==================== Mock Components ====================

# 1. Mock Model (Simple CNN)
class SimpleNet(nn.Module):
    def __init__(self):
        super(SimpleNet, self).__init__()
        self.conv1 = nn.Conv2d(3, 6, 5)
        self.pool = nn.MaxPool2d(2, 2)
        self.conv2 = nn.Conv2d(6, 16, 5)
        self.fc1 = nn.Linear(16 * 5 * 5, 120)
        self.fc2 = nn.Linear(120, 84)
        self.fc3 = nn.Linear(84, 10)

    def forward(self, x):
        x = self.pool(torch.relu(self.conv1(x)))
        x = self.pool(torch.relu(self.conv2(x)))
        x = x.view(-1, 16 * 5 * 5)
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        x = self.fc3(x)
        return x

# 2. Mock Data (Random Noise)
def get_mock_dataloader():
    # Create 100 random images (3x32x32) and labels (0-9)
    # Intentionally skew labels to test Entropy check (Non-IID)
    # 80 samples of class 0, 20 samples of class 1
    data = torch.randn(100, 3, 32, 32)
    labels = torch.cat([torch.zeros(80), torch.ones(20)]).long()
    dataset = TensorDataset(data, labels)
    return DataLoader(dataset, batch_size=10, shuffle=True)

# ==================== Demo Flow ====================

def main():
    print("🚀 启动 TMAA Trust Report 生成演示...")
    
    # 1. Initialize TEE and Sidecar
    print("\n[Stage 1] 初始化安全环境...")
    tee = SimulatedTEE(device_id="Demo-Device-001")
    sidecar = TMAA_Sidecar(tee_hardware=tee, pid=os.getpid())
    sidecar.start_monitoring()
    
    # 2. Data Inspection (L3 Audit)
    print("\n[Stage 2] 执行数据审计 (L3 Zero-Knowledge Inspection)...")
    net = SimpleNet()
    dataloader = get_mock_dataloader()
    sidecar.scan_data(dataloader, net=net, device="cpu")
    
    # 3. Simulate Training (L2 Behavior)
    print("\n[Stage 3] 模拟本地训练...")
    # Capture old params
    old_params = [p.clone().detach() for p in net.parameters()]
    
    # ... Training loop simulation (sleep to show duration check) ...
    time.sleep(1.0) # > 0.5s threshold
    
    # Simulate parameter update (random noise)
    with torch.no_grad():
        for p in net.parameters():
            p.add_(torch.randn_like(p) * 0.1)
            
    # Calculate Layer-wise updates
    layer_updates = []
    for old_p, new_p in zip(old_params, net.parameters()):
        diff = torch.norm(new_p - old_p, p=2).item()
        layer_updates.append(diff)
        
    duration = 1.05
    meta_data = {
        "round": 1,
        "duration": duration,
        "epochs": 1,
        "sample_count": 100,
        "device_type": "cpu",
        "layer_updates": [round(x, 4) for x in layer_updates],
        "attack_mode": "none"  # Honest client
    }
    
    # 4. Generate Trust Report
    print("\n[Stage 4] 生成最终可信报告 (Trust Report)...")
    trust_package = sidecar.generate_trust_report(meta_data)
    sidecar.stop_monitoring()
    
    # 5. Review Content
    print("\n" + "="*60)
    print("📋 发往 Server 的完整数据包 (JSON Payload)")
    print("="*60)
    print(json.dumps(trust_package, indent=4, ensure_ascii=False))
    print("="*60)
    
    # Verify signature
    is_valid = tee.verify_signature(
        trust_package['trust_report'], 
        trust_package['signature'], 
        tee.public_key
    )
    print(f"\n🔐 签名验证结果: {'✅ Passed' if is_valid else '❌ Failed'}")

if __name__ == "__main__":
    main()
