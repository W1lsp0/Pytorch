"""
==============================================================================
🚓 TMAA Sidecar 伴随监控代理
==============================================================================
本模块定义了从属模式(Sidecar)的监控代理。

设计理念:
    像 Kubernetes Pod 中的 Sidecar 容器一样，该线程与主训练进程
    虽然运行在同一空间(或独立进程)，但负责正交的监控任务。

职责:
    1. 启动并守护 SystemMonitor (L1/L2/L4 监控)
    2. 按需调用 DataInspector (L3 审计)
    3. 整合所有情报，调用 TEE 硬件生成"可信报告" (Trust Report)

作者: Flwr 联邦学习项目
==============================================================================
"""

import threading
import time
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional

from .monitor import SystemMonitor
from .inspector import DataInspector

class TMAA_Sidecar(threading.Thread):
    def __init__(self, tee_hardware, pid: int, use_simulation: bool = False):
        super().__init__()
        self.tee = tee_hardware
        self.pid = pid
        # 传递 device_id 给 monitor 用于数据库读取
        self.monitor = SystemMonitor(pid, device_id=tee_hardware.device_id, use_simulation=use_simulation)
        self.data_metrics = {}
        self.running = False
        self.report = None
        self.daemon = True # 设置为守护线程，随主进程退出

    def start_monitoring(self):
        """启动伴随监控"""
        self.running = True
        self.start()  # 启动线程 run()

    def stop_monitoring(self):
        """停止监控"""
        self.running = False
        # 等待线程结束（但通常作为 Sidecar，它可能一直运行直到任务结束）
        # self.join() 

    def scan_data(self, dataloader, net=None, device=None):
        """
        [Trigger] 触发 L3 数据审计
        
        通常在 fit() 开始前调用，对本地数据进行一次"体检"。
        """
        # 实例化 Inspector (若未传入 device 则默认 cpu)
        target_device = device if device else "cpu"
        inspector = DataInspector(target_device)
        
        # 执行全量审计
        if net:
            # 返回完整的 metrics 字典 (包括 initial_loss 等)
            self.data_metrics = inspector.inspect(net, dataloader)
        else:
            print("⚠️ [TMAA] Warning: No net provided, skipping deep inspection.")
            self.data_metrics = {}

    def run(self):
        """Sidecar 主循环: 持续执行资源与网络监控"""
        print(f"🛡️ [TMAA] Sidecar 守护进程启动 (Target PID: {self.pid})")

        # L1: 初始完整性检查 (检查 key files)
        self.monitor.check_file_integrity(["client_main.py", "model.py"])

        while self.running:
            # L2 & L4: 周期性采样 (1Hz)
            self.monitor.sample_resources()
            self.monitor.check_network()
            time.sleep(1.0) 

    def generate_trust_report(self, training_meta: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成最终的可信报告 (Trust Report)
        
        该报告汇总了：
        1. 硬件身份 (TEE ID)
        2. 系统完整性状态 (File Integrity)
        3. 运行时行为指纹 (CPU Volatility)
        4. 数据审计结果 (Data Metrics)
        5. 训练元数据 (Client Reported)
        
        最后由从 TEE 获取的私钥签名。
        """
        # 计算资源波动率
        cpu_volatility = self.monitor.calculate_volatility()
        
        # 构造报告载荷
        report_payload = {
            "header": {
                "device_id": self.tee.device_id,
                "timestamp": datetime.now().isoformat(),
                "pid": self.pid,
                "schema_version": "1.0"
            },
            "metrics": {
                "system_integrity": {
                    "file_tampered": not self.monitor.integrity_status,
                    "network_anomalies": self.monitor.network_violations
                },
                "behavior_fingerprint": {
                    "cpu_volatility": round(cpu_volatility, 4),
                    "description": "High volatility > 5 indicates valid training"
                },
                "data_health_audit": self.data_metrics,  # 零知识审计结果
                "client_reported_meta": training_meta    # 客户端自报数据
            }
        }

        # 🔑 关键: 使用 TEE 信任根签名
        signature = self.tee.sign_data(report_payload)

        final_package = {
            "trust_report": report_payload,
            "signature": signature
        }

        print(f"\n🔐 [TMAA] 已生成可信报告 (Signed by {self.tee.device_id})")
        # print(f"   Signature: {signature[:16]}...{signature[-8:]}")
        return final_package