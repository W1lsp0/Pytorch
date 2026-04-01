#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
文件名: client.py
功能: 联邦学习客户端 (Federated Learning Client)
描述:
    本模块实现了 Flower (flwr) 客户端逻辑，负责：
    1. 本地数据加载与预处理 (支持投毒攻击)。
    2. 本地模型训练 (Local Training) 与评估 (Local Evaluation)。
    3. 与 TMAA (Trusted Model Audit Agent) 集成，保障训练过程的可信度。
    4. 向 Dashboard 实时汇报节点状态 (Loss, ASR 等)。

    核心类:
        - MyClient: 继承自 flwr.client.NumPyClient，实现 fit/evaluate 接口。

作者: Flwr 联邦学习项目组
Refactored: 2026-02-11
==============================================================================
"""

import sys
import os

# ==================== 系统环境配置 ====================
# 1. 修复 stdout 缓冲问题 (防止日志乱序/延迟)
if not sys.stdout.isatty():
    import io
    sys.stdout = io.TextIOWrapper(
        open(sys.stdout.fileno(), 'wb', 0),
        write_through=True
    )
    sys.stderr = io.TextIOWrapper(
        open(sys.stderr.fileno(), 'wb', 0),
        write_through=True
    )

# 2. 解决 Windows 中文乱码问题
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
# ====================================================

import flwr as fl
import torch
import torch.nn as nn
import time
import json
import logging
from typing import Dict, Tuple, List, Any, Optional

# 项目模块导入
from model import get_resnet18
from dataset import load_data
from poison.attack_wrapper import create_backdoor_test_loader, ATTACK_BACKDOOR, ATTACK_CLEAN_LABEL
from poison.db_manager import DBManager

# TMAA 安全模块导入
from tmaa.tee_sim import SimulatedTEE
from tmaa.sidecar import TMAA_Sidecar

# Refactored Modules
from engine import train, test
from status import StatusReporter

# ==================== 日志配置 ====================
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s %(levelname)s: %(message)s', 
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("Client")

# ==================== 全局配置常量 ====================
CLIENT_ID = int(os.environ.get("CLIENT_ID", 0))
TOTAL_CLIENTS = int(os.environ.get("TOTAL_CLIENTS", 2))
DEVICE = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

# 攻击配置读取
ATTACK_TYPE = None
if 'ATTACK_TYPE' in os.environ:
    val = os.environ['ATTACK_TYPE'].lower()
    valid_attacks = [
        'flip',
        'label_flip',
        'backdoor',
        'directed_label_flip',
        'clean_label',
        'semantic',
        'sign_flip',
        'gradient_scale',
    ]
    if val in valid_attacks:
        ATTACK_TYPE = val
    elif val not in ['none', '']:
        logger.warning(f"⚠️  配置警告: 未知的攻击类型 '{val}'，已忽略。")

POISON_RATE = float(os.environ.get("POISON_RATE", 0.0))
TARGET_LABEL = int(os.environ.get("TARGET_LABEL", 0))
SCALE_FACTOR = float(os.environ.get("SCALE_FACTOR", 10.0))

def print_banner(device: torch.device):
    """打印客户端启动横幅 (原子输出，防止多线程交错)"""
    lines = [
        "",
        "╔" + "═"*58 + "╗",
        f"║  🚀 联邦学习客户端启动 (ID: {CLIENT_ID}){' '*23}║",
        "╠" + "═"*58 + "╣",
        f"║  💻 计算设备:  {str(device).ljust(41)} ║",
        f"║  🛡️  TMAA 监控:  已启用 (Enabled){' '*27} ║",
    ]
    if ATTACK_TYPE:
        lines.append(f"║  😈 攻击模式:  {ATTACK_TYPE.upper().ljust(41)} ║")
        if ATTACK_TYPE in ("sign_flip", "gradient_scale"):
            lines.append(f"║  📈 缩放系数:  {str(SCALE_FACTOR).ljust(41)} ║")
        else:
            lines.append(f"║  🎯 目标标签:  {str(TARGET_LABEL).ljust(41)} ║")
    else:
        lines.append(f"║  ✅ 运行模式:  正常训练 (Honest){' '*24} ║")
    lines.append("╚" + "═"*58 + "╝")
    lines.append("")
    print("\n".join(lines))


# ==================== Flower Client 定义 ====================

class MyClient(fl.client.NumPyClient):
    """
    自定义 Flower 客户端类，集成 TMAA 与投毒逻辑
    """
    
    def __init__(
        self, 
        net: nn.Module, 
        trainloader: torch.utils.data.DataLoader, 
        testloader: torch.utils.data.DataLoader, 
        backdoor_testloader: torch.utils.data.DataLoader, 
        clean_label_testloader: torch.utils.data.DataLoader, 
        tmaa_agent: Any,
        status_reporter: StatusReporter
    ):
        self.net = net
        self.trainloader = trainloader
        self.testloader = testloader
        
        # 两个专用的 ASR 测试集
        self.backdoor_testloader = backdoor_testloader       # 右下角触发器
        self.clean_label_testloader = clean_label_testloader # 左上角触发器
        
        self.tmaa_agent = tmaa_agent
        self.status = status_reporter
        
        # Local ASR Cache (Backdoor, CleanLabel)
        self.last_local_asr = (0.0, 0.0)

    def get_parameters(self, config):
        """获取本地模型参数"""
        return [val.cpu().numpy() for _, val in self.net.state_dict().items()]

    def fit(self, parameters, config):
        """
        [训练阶段]
        接收全局参数 -> 本地训练 -> 返回更新后的参数
        在此过程中集成 TMAA 监控。
        """
        # 1. 加载全局参数
        params_dict = zip(self.net.state_dict().keys(), parameters)
        state_dict = {k: torch.tensor(v).to(DEVICE) for k, v in params_dict}
        self.net.load_state_dict(state_dict, strict=True)
        
        server_round = config.get("current_round", -1)
        logger.info(f"\n" + "━"*60)
        logger.info(f"🔄 Round {server_round} | 启动本地训练任务")
        logger.info("━"*60)

        # Dashboard: 更新状态为 Training
        self.status.update(status="Training", round_num=server_round)

        # ====================== TMAA 介入 [Phase 1: Pre-Train] ======================
        logger.info(f"🛡️  [TMAA Step 1] 启动 Sidecar 监控...")
        self.tmaa_agent.start_monitoring()

        logger.info(f"🛡️  [TMAA Step 2] 执行 L3 数据隐私审计...")
        # 扫描数据分布，确保隐私合规 (此处为模拟)
        self.tmaa_agent.scan_data(self.trainloader, self.net, DEVICE)
        # =========================================================================

        # 2. 执行本地训练
        # 保存初始权重 (W_global) 用于后续计算更新量 (Boosting) & 层级更新幅度 (Layer-wise Updates)
        w_global = [p.clone().detach() for p in self.net.parameters()]
        
        start_time = time.time()
        # [Capture History] 捕获训练过程数据
        # [Updated] Pass tmaa_agent for Phase Signals
        train_history = train(self.net, self.trainloader, epochs=3, device=DEVICE, tmaa_agent=self.tmaa_agent) 
        duration = time.time() - start_time
        logger.info(f"✅ 本地训练完成 (耗时: {duration:.2f}s)")

        # ====================== [New Feature] Layer-wise Gradient Consistency (层级更新一致性) ======================
        # 检测 "Freezing Attack" (冻结攻击): 恶意节点可能冻结大部分层，只训练最后一层
        # 计算每一层参数的 L2 范数变化量: ||W_new - W_old||
        layer_updates = []
        new_params = list(self.net.parameters())
        with torch.no_grad():
            for old_p, new_p in zip(w_global, new_params):
                diff = torch.norm(new_p - old_p, p=2).item()
                layer_updates.append(diff)
        
        # 将层级更新幅度加入元数据，供 TMAA 审计
        logger.info(f"    📏 Layer Updates: {[round(x, 4) for x in layer_updates[-5:]]}...")
        # ========================================================================================================

        # ====================== [New Feature] 本地模型攻击效果评估 ======================
        logger.info(f"📊 正在评估本地模型 (Post-Training Evaluation)...")
        local_loss, local_acc = test(self.net, self.testloader, DEVICE)
        
        # 评估两种攻击触发器的响应情况
        _, local_asr_b = test(self.net, self.backdoor_testloader, DEVICE)     # Backdoor (右下角)
        _, local_asr_c = test(self.net, self.clean_label_testloader, DEVICE)  # Clean Label (左上角)
        
        # 更新全局缓存 (用于 evaluate 阶段汇报)
        self.last_local_asr = (local_asr_b, local_asr_c)

        # Dashboard: 汇报 Training 完成状态 + 本地 ASR
        loss_str = f"{local_loss:.4f}"
        
        # 格式化 ASR 字符串: "L:B99 C12|G:?"
        local_asr_str = f"B{local_asr_b*100:.0f}% C{local_asr_c*100:.0f}%"
        combined_asr_str = f"L:{local_asr_str}|G:?"
        
        self.status.update(status="Trained", round_num=server_round, loss=loss_str, asr=combined_asr_str)
        
        logger.info(f"   -> 本地 ASR (Backdoor):    {local_asr_b*100:.1f}%")
        logger.info(f"   -> 本地 ASR (CleanLabel):  {local_asr_c*100:.1f}%")
        # ===================================================================================

        # ====================== [Model Poisoning] 参数更新后处理 ======================
        # sign_flip:      ΔW <- -scale * ΔW
        # gradient_scale: ΔW <-  scale * ΔW
        if ATTACK_TYPE in ("sign_flip", "gradient_scale"):
            with torch.no_grad():
                for old_p, new_p in zip(w_global, self.net.parameters()):
                    delta = new_p.data - old_p.data
                    if ATTACK_TYPE == "sign_flip":
                        delta = -SCALE_FACTOR * delta
                    else:
                        delta = SCALE_FACTOR * delta
                    new_p.data.copy_(old_p.data + delta)

            if ATTACK_TYPE == "sign_flip":
                logger.info(f"😈 [Sign-Flip Attack] 对更新量 (ΔW) 执行符号反转并缩放 {SCALE_FACTOR}")
            else:
                logger.info(f"😈 [Gradient-Scale Attack] 对更新量 (ΔW) 乘以放大系数 {SCALE_FACTOR}")
        # ===================================================================================

        # ====================== TMAA 介入 [Phase 2: Post-Train] ======================
        logger.info(f"🛡️  [TMAA Step 3] 停止监控并生成可信证明...")
        self.tmaa_agent.stop_monitoring()

        # 收集元数据用于生成报告
        meta_data = {
            "round": server_round,
            "duration": round(duration, 2),
            "epochs": 1,
            "sample_count": len(self.trainloader.dataset),
            "device_type": str(DEVICE),
            "layer_updates": [round(x, 6) for x in layer_updates],  # 记录每一层的更新幅度
            "training_curve": train_history  # 记录 Loss 和 GradNorm 变化曲线
        }

        # 生成可信报告包 (Trust Package)
        trust_package = self.tmaa_agent.generate_trust_report(meta_data)
        # =========================================================================

        # 3. 返回训练结果
        # Metrics Payload: 将 TMAA 报告打包回传给服务器
        metrics_payload = {
            "trust_report_json": json.dumps(trust_package),
            "real_client_id": CLIENT_ID
        }
        
        return self.get_parameters(config={}), len(self.trainloader.dataset), metrics_payload

    def evaluate(self, parameters, config):
        """
        [评估阶段]
        接收全局模型 -> 本地评估 -> 返回指标
        """
        # 1. 加载全局参数
        params_dict = zip(self.net.state_dict().keys(), parameters)
        state_dict = {k: torch.tensor(v).to(DEVICE) for k, v in params_dict}
        self.net.load_state_dict(state_dict, strict=True)

        # 2. 评估正常任务指标 (Acc, Loss)
        loss, accuracy = test(self.net, self.testloader, DEVICE)
        
        # 3. 评估攻击指标 (ASR)
        # B: Backdoor (右下角), C: Clean Label (左上角)
        _, asr_b = test(self.net, self.backdoor_testloader, DEVICE)
        _, asr_c = test(self.net, self.clean_label_testloader, DEVICE)
        
        # 4. 打印评估报告
        # 原子输出评估报告 (防止多线程交错)
        eval_report = "\n".join([
            f"\n    ┌{'─'*50}┐",
            f"    │  📊 客户端 {CLIENT_ID} 本地评估报告 (Global Model){' '*4}│",
            f"    ├{'─'*50}┤",
            f"    │  ✅ 正常准确率 (ACC) : {accuracy * 100:.2f}%{' '*18}│",
            f"    │  💀 Global BD ASR    : {asr_b * 100:.2f}%{' '*18}│",
            f"    │  💀 Global CL ASR    : {asr_c * 100:.2f}%{' '*18}│",
            f"    └{'─'*50}┘\n"
        ])
        logger.info(eval_report)

        # Dashboard: 更新 Evaluated 状态
        # 获取缓存的 Local ASR (从 fit 阶段)
        loc_b, loc_c = self.last_local_asr
            
        # 拼接字符串: "L:B99 C12|G:B45 C45"
        loc_str = f"B{loc_b*100:.0f}% C{loc_c*100:.0f}%"
        glo_str = f"B{asr_b*100:.0f}% C{asr_c*100:.0f}%"
        combined_asr_str = f"L:{loc_str}|G:{glo_str}"
        
        loss_str = f"{loss:.4f}"
        server_round = config.get("current_round", "-")
        self.status.update(status="Evaluated", round_num=server_round, loss=loss_str, asr=combined_asr_str)

        # 返回指标给服务器聚合
        return float(loss), len(self.testloader.dataset), {
            "accuracy": float(accuracy),
            "asr": float(asr_b),         # 主要 ASR (Backdoor)
            "asr_clean": float(asr_c)    # 次要 ASR (Clean Label)
        }

# ==================== 主入口 ====================

def main():
    """
    客户端主程序入口
    """
    
    # 1. 状态数据库初始化
    db_manager = None
    try:
        db_manager = DBManager()
        print("✅ [Status] 已连接状态数据库 (Monitoring DB)")
    except Exception as e:
        print(f"⚠️ [Status] 状态数据库连接失败: {e}")
        
    status_reporter = StatusReporter(db_manager, CLIENT_ID, ATTACK_TYPE)

    # 2. 打印启动横幅
    print_banner(DEVICE)

    # 3. 数据加载
    # 加载针对当前 Client 分配的数据分片
    trainloader, testloader = load_data(
        client_id=CLIENT_ID,
        total_clients=TOTAL_CLIENTS,
        attack_type=ATTACK_TYPE,
        poison_rate=POISON_RATE,
        target_label=TARGET_LABEL
    )
    
    # 4. 创建 ASR 评估专用测试集 (双触发器)
    # 4.1 Backdoor 测试集 (右下角触发器)
    backdoor_testloader = create_backdoor_test_loader(
        batch_size=64,
        num_workers=0,
        target_label=TARGET_LABEL,
        trigger_type=ATTACK_BACKDOOR
    )
    
    # 4.2 Clean Label 测试集 (左上角触发器)
    clean_label_testloader = create_backdoor_test_loader(
        batch_size=64,
        num_workers=0,
        target_label=TARGET_LABEL,
        trigger_type=ATTACK_CLEAN_LABEL
    )
    
    # 5. 模型初始化
    net = get_resnet18().to(DEVICE)
    
    # 6. TMAA 安全组件初始化
    print("🔐 [Init] 正在初始化可信执行环境 (TEE) 与监控代理...")
    use_simulation = os.environ.get("USE_SIMULATION", "0") == "1"
    if use_simulation:
        print("    ⚠️  [Config] 启用数据库仿真监控模式 (Simulation Mode)")
        
    tee_hardware = SimulatedTEE(device_id=f"worker_{CLIENT_ID:04d}")
    tmaa_agent = TMAA_Sidecar(tee_hardware, pid=os.getpid(), use_simulation=use_simulation)

    # Dashboard: 更新为已连接状态
    status_reporter.update(status="Connected")

    # 7. 启动 Flower 客户端
    server_addr = "127.0.0.1:8080"
    print(f"🔗 正在连接聚合服务器: {server_addr} ...")
    
    # 启动长时间运行的客户端进程
    fl.client.start_numpy_client(
        server_address=server_addr, 
        client=MyClient(
            net=net, 
            trainloader=trainloader, 
            testloader=testloader, 
            backdoor_testloader=backdoor_testloader, 
            clean_label_testloader=clean_label_testloader, 
            tmaa_agent=tmaa_agent,
            status_reporter=status_reporter
        )
    )

if __name__ == "__main__":
    main()
