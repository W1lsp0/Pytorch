import sys
import os

# ==================== 子进程保护机制 (文件锁方案) ====================
# 问题: joblib/loky 使用 spawn/exec 方式启动新 Python 解释器
#       子进程会重新导入 client.py 作为 __main__，导致 main() 被意外执行
#
# 解决方案: 使用文件锁 + PID 跟踪
#   1. 主进程启动时创建锁文件 /tmp/flwr_client_{CLIENT_ID}.lock
#   2. 子进程发现锁文件存在且持有进程仍然存活，则跳过 main()

def _get_lock_file_path() -> str:
    """获取当前客户端的锁文件路径"""
    client_id = os.environ.get("CLIENT_ID", "0")
    return f"/tmp/flwr_client_{client_id}.lock"

def _is_main_process_alive(lock_path: str) -> bool:
    """
    检查锁文件中记录的主进程是否仍在运行
    """
    if not os.path.exists(lock_path):
        return False
    try:
        with open(lock_path, 'r') as f:
            main_pid = int(f.read().strip())
        # 检查该 PID 是否存活
        os.kill(main_pid, 0)  # signal 0 仅检测，不发送信号
        return True  # 进程存活
    except (ValueError, ProcessLookupError, PermissionError, FileNotFoundError):
        return False  # 进程不存在或无权限

def _acquire_lock() -> bool:
    """
    尝试获取锁 (仅主进程调用)
    Returns: True 表示成功获取锁，False 表示已被其他进程持有
    """
    lock_path = _get_lock_file_path()
    
    # 如果锁已存在且持有进程存活，则当前进程是子进程
    if _is_main_process_alive(lock_path):
        return False
    
    # 创建/更新锁文件，写入当前 PID
    with open(lock_path, 'w') as f:
        f.write(str(os.getpid()))
    return True

# 尝试获取锁，判断是否为主进程
_IS_MAIN_PROCESS = _acquire_lock()

if not _IS_MAIN_PROCESS:
    # 子进程：静默跳过，让模块继续加载但不执行 main()
    pass
else:
    print(f"[DEBUG] 主进程启动 PID: {os.getpid()}")

# 防止 joblib/sklearn OpenMP 多线程
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1" 
os.environ["LOKY_MAX_CPU_COUNT"] = "1" 

import flwr as fl
import torch
import torch.optim as optim
import torch.nn as nn
import time
import json
from typing import Dict, Tuple, List, Any

# ==================== 解决 Windows 中文乱码问题 ====================
# 强制将标准输出和错误输出设置为 UTF-8 编码
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        # Python < 3.7
        pass
# ================================================================

# 项目模块导入
from model import get_resnet18
from dataset import load_data
from poison import create_backdoor_test_loader, CIFAR10_CLASSES

# TMAA 安全模块导入
from tmaa.tee_sim import SimulatedTEE
from tmaa.sidecar import TMAA_Sidecar

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger("TMAA_Client")

# ==================== 全局配置 ====================
CLIENT_ID = int(os.environ.get("CLIENT_ID", 0))
TOTAL_CLIENTS = int(os.environ.get("TOTAL_CLIENTS", 2))
DEVICE = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

# 获取攻击配置
ATTACK_TYPE = None
if 'ATTACK_TYPE' in os.environ:
    val = os.environ['ATTACK_TYPE'].lower()
    if val in ['flip', 'label_flip', 'backdoor', 'directed_label_flip', 'clean_label', 'semantic']:
        ATTACK_TYPE = val
    elif val not in ['none', '']:
        print(f"⚠️  未知攻击类型: {val}，已忽略")

POISON_RATE = float(os.environ.get("POISON_RATE", 0.0))
TARGET_LABEL = int(os.environ.get("TARGET_LABEL", 0))

# ==================== 状态同步 (Dashboard Communication) ====================
# 使用数据库进行状态同步
from poison.db_manager import DBManager
db_manager = None  # Global, initialized in main

def update_status_monitor(status="Waiting", round_num="-", loss="-", asr="-"):
    """
    更新客户端状态到数据库 (供 Dashboard 读取)
    """
    if db_manager:
        data = {
            "type": "BAD" if ATTACK_TYPE else "GOOD",
            "attack": ATTACK_TYPE.upper() if ATTACK_TYPE else "HONEST",
            "round": round_num,
            "loss": loss,
            "asr": asr,
            "status": status
        }
        db_manager.update_client_status(CLIENT_ID, data)

# ==================== ASCII Banner ====================
def print_banner(device):
    print("\n" + "╔" + "═"*58 + "╗")
    print(f"║  🚀 联邦学习客户端启动 (Client ID: {CLIENT_ID}){' '*16}║")
    print("╠" + "═"*58 + "╣")
    print(f"║  💻 计算设备:  {str(device).ljust(41)} ║")
    print(f"║  🛡️  TMAA 监控:  Enabled{' '*34} ║")
    if ATTACK_TYPE:
        print(f"║  😈 攻击模式:  {ATTACK_TYPE.upper().ljust(41)} ║")
    else:
        print(f"║  ✅ 运行模式:  正常训练 (Honest){' '*24} ║")
    print("╚" + "═"*58 + "╝\n")

# ==================== 训练与评估逻辑 ====================

def train(net, trainloader, epochs):
    """本地训练循环"""
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.SGD(net.parameters(), lr=0.01, momentum=0.9)
    net.train()
    
    print(f"    🏋️  开始训练 ({epochs} Epochs)...")
    for epoch in range(epochs):
        running_loss = 0.0
        for i, (images, labels) in enumerate(trainloader):
            images, labels = images.to(DEVICE), labels.to(DEVICE)
            optimizer.zero_grad()
            loss = criterion(net(images), labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item()
        
        # 模拟 epoch 间耗时，便于 Observation
        time.sleep(0.1)
        avg_loss = running_loss / len(trainloader)
        print(f"       Epoch {epoch+1}/{epochs} | Loss: {avg_loss:.4f}")

def test(net, testloader) -> Tuple[float, float]:
    """
    通用评估函数
    Returns: (loss, accuracy)
    """
    criterion = nn.CrossEntropyLoss()
    correct, total, loss = 0, 0, 0.0
    
    net.eval()
    with torch.no_grad():
        for images, labels in testloader:
            images, labels = images.to(DEVICE), labels.to(DEVICE)
            outputs = net(images)
            loss += criterion(outputs, labels).item()
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
            
    avg_loss = loss / len(testloader.dataset) if len(testloader.dataset) else 0
    accuracy = correct / total if total else 0
    return avg_loss, accuracy

# ==================== Flower Client 定义 ====================

class MyClient(fl.client.NumPyClient):
    
    def __init__(self, net, trainloader, testloader, backdoor_testloader, tmaa_agent):
        self.net = net
        self.trainloader = trainloader
        self.testloader = testloader
        self.backdoor_testloader = backdoor_testloader
        self.tmaa_agent = tmaa_agent

    def get_parameters(self, config):
        return [val.cpu().numpy() for _, val in self.net.state_dict().items()]

    def fit(self, parameters, config):
        """
        本地训练回调
        在这里集成 TMAA 监控流程: 启动 -> 审计 -> 训练 -> 停止 -> 生成报告
        """
        # 1. 更新模型参数
        params_dict = zip(self.net.state_dict().keys(), parameters)
        state_dict = {k: torch.tensor(v).to(DEVICE) for k, v in params_dict}
        self.net.load_state_dict(state_dict, strict=True)
        
        server_round = config.get("current_round", -1)
        logger.info(f"\n" + "━"*60)
        logger.info(f"🔄 Round {server_round} | 开始本地训练任务")
        logger.info("━"*60)

        # [Dashboard] Update status
        update_status_monitor(status="Training", round_num=server_round)

        # ====================== TMAA 介入 [Phase 1: Pre-Train] ======================
        logger.info(f"🛡️  [Step 1] TMAA Sidecar 启动监控...")
        self.tmaa_agent.start_monitoring()

        logger.info(f"🛡️  [Step 2] TMAA 执行 L3 数据隐私层审计...")
        # 在训练前对数据分布进行"体检"
        self.tmaa_agent.scan_data(self.trainloader, self.net, DEVICE)
        # =========================================================================

        # 2. 执行本地训练
        start_time = time.time()
        train(self.net, self.trainloader, epochs=1)
        duration = time.time() - start_time
        logger.info(f"✅ 本地训练完成 (耗时: {duration:.2f}s)")

        # ====================== TMAA 介入 [Phase 2: Post-Train] ======================
        logger.info(f"🛡️  [Step 3] TMAA 停止监控并生成可信报告...")
        self.tmaa_agent.stop_monitoring()

        # 收集训练元数据 (Client 自报的部分)
        meta_data = {
            "round": server_round,
            "duration": round(duration, 2),
            "epochs": 1,
            "sample_count": len(self.trainloader.dataset),
            "device_type": str(DEVICE)
        }

        # 生成最终的 Trust Package (含签名)
        trust_package = self.tmaa_agent.generate_trust_report(meta_data)
        # =========================================================================

        # 3. 返回结果给 Server
        # 注意: metrics 只能传简单 kv，复杂 json 需要序列化
        metrics_payload = {
            "trust_report_json": json.dumps(trust_package)
        }
        
        return self.get_parameters(config={}), len(self.trainloader.dataset), metrics_payload

    def evaluate(self, parameters, config):
        """
        模型评估回调
        同时评估正常准确率 (MTA) 和后门攻击成功率 (ASR)
        """
        # 1. 更新参数
        params_dict = zip(self.net.state_dict().keys(), parameters)
        state_dict = {k: torch.tensor(v).to(DEVICE) for k, v in params_dict}
        self.net.load_state_dict(state_dict, strict=True)

        # 2. 评估正常准确率 (Main Task Accuracy)
        loss, accuracy = test(self.net, self.testloader)
        
        # 3. 评估后门攻击成功率 (Attack Success Rate)
        # 即: 针对所有带触发器的图片，有多少被识别为了 target_label
        _, asr = test(self.net, self.backdoor_testloader)
        
        # 4. 打印评估报告
        logger.info(f"\n    ┌{'─'*45}┐")
        logger.info(f"    │  📊 客户端 {CLIENT_ID} 本地评估报告{' '*17}│")
        logger.info(f"    ├{'─'*45}┤")
        logger.info(f"    │  ✅ 正常准确率 (MTA): {accuracy * 100:.2f}%{' '*17}│")
        logger.info(f"    │  💀 后门成功率 (ASR): {asr * 100:.2f}%{' '*17}│")
        logger.info(f"    └{'─'*45}┘\n")

        # [Dashboard] Update status
        acc_str = f"{accuracy*100:.1f}%"
        asr_str = f"{asr*100:.1f}%"
        loss_str = f"{loss:.4f}"
        server_round = config.get("current_round", "-")
        update_status_monitor(status="Evaluated", round_num=server_round, loss=loss_str, asr=asr_str)

        # 返回 metrics 给服务器聚合
        return float(loss), len(self.testloader.dataset), {
            "accuracy": float(accuracy),
            "asr": float(asr)
        }

def main():
    # ==================== 防止子进程重复执行 ====================
    # 使用模块顶层的文件锁检测结果
    # 如果锁已被其他进程持有，说明当前进程是 loky 子进程
    if not _IS_MAIN_PROCESS:
        return  # 子进程静默返回

    global db_manager
    
    # 状态数据库初始化
    try:
        db_manager = DBManager()
        print("✅ [Status] Connected to DB for status updates.")
    except Exception as e:
        print(f"⚠️ [Status] DB Connection failed: {e}")

    # Banner
    print_banner(DEVICE)

    # 1. 加载本地数据
    trainloader, testloader = load_data(
        client_id=CLIENT_ID,
        total_clients=TOTAL_CLIENTS,
        attack_type=ATTACK_TYPE,
        poison_rate=POISON_RATE,
        target_label=TARGET_LABEL
    )
    
    # 2. 创建后门测试集（专用于评估 ASR）
    backdoor_testloader = create_backdoor_test_loader(
        batch_size=64,
        num_workers=0,
        target_label=TARGET_LABEL
    )
    
    # 3. 初始化模型
    net = get_resnet18().to(DEVICE)
    
    # ==================== TMAA 初始化 ====================
    print("🔐 [Init] 正在初始化可信执行环境 (TEE) 与监控代理...")
    
    # 获取仿真标志 (默认 False)
    USE_SIMULATION = os.environ.get("USE_SIMULATION", "0") == "1"
    if USE_SIMULATION:
        print("    ⚠️  [Config] 启用数据库仿真监控 (L4 Simulation Mode)")
        
    tee_hardware = SimulatedTEE(device_id=f"device_{CLIENT_ID:03d}")
    tmaa_agent = TMAA_Sidecar(tee_hardware, pid=os.getpid(), use_simulation=USE_SIMULATION)

    # [Dashboard] Init
    update_status_monitor(status="Connected")

    # 启动 Flower 客户端
    server_addr = "127.0.0.1:8080"
    print(f"🔗 正在连接服务器: {server_addr} ...")
    
    fl.client.start_numpy_client(
        server_address=server_addr, 
        client=MyClient(net, trainloader, testloader, backdoor_testloader, tmaa_agent)
    )

if __name__ == "__main__":
    main()