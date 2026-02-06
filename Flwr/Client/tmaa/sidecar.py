# client/tmaa/sidecar.py (TMAA 主控单例)
import threading
import time
import os
import json
from datetime import datetime
from .monitor import SystemMonitor
from .inspector import DataInspector


class TMAA_Sidecar(threading.Thread):
    def __init__(self, tee_hardware, pid):
        super().__init__()
        self.tee = tee_hardware
        self.pid = pid
        self.monitor = SystemMonitor(pid)
        self.data_metrics = {}
        self.running = False
        self.report = None

    def start_monitoring(self):
        """启动伴随监控"""
        self.running = True
        self.start()  # 启动线程 run()

    def stop_monitoring(self):
        """停止监控"""
        self.running = False
        self.join()  # 等待线程结束

    def scan_data(self, dataloader, net=None, device=None):
        """触发 L3 数据审计"""
        # 1. 静态数据审计
        self.data_metrics = DataInspector.audit_privacy_safe_metrics(dataloader)

        # 2. 初始 Loss (可选，用于检测标签翻转)
        if net and device:
            init_loss = DataInspector.calculate_initial_loss(net, dataloader, device)
            self.data_metrics["initial_loss"] = round(init_loss, 4)

    def run(self):
        """Sidecar 主循环: 资源与网络监控"""
        print(f"🛡️ [TMAA] 守护进程启动，正在监控 PID: {self.pid}")

        # L1: 初始完整性检查
        self.monitor.check_file_integrity(["client_main.py", "model.py"])

        while self.running:
            # L2 & L4: 周期性采样
            self.monitor.sample_resources()
            self.monitor.check_network()
            time.sleep(1.0)  # 采样频率 1Hz

    def generate_trust_report(self, training_meta):
        """
        生成最终的可信报告 (包含前面所有的监控数据)
        training_meta: 来自 Worker 的主动上报数据 (Epochs, Final Loss)
        """
        # 计算资源波动率
        cpu_volatility = self.monitor.calculate_volatility()

        report_payload = {
            "header": {
                "device_id": self.tee.device_id,
                "timestamp": datetime.now().isoformat(),
                "pid": self.pid
            },
            "metrics": {
                "system": {
                    "file_integrity": self.monitor.integrity_status,
                    "network_violations": self.monitor.network_violations
                },
                "behavior": {
                    "resource_fingerprint": {
                        "cpu_volatility": round(cpu_volatility, 4),
                        # "avg_cpu": ...
                    },
                    "training_meta": training_meta  # 如: through-put
                },
                "data_health": self.data_metrics  # 零知识标量
            }
        }

        # 关键: 使用 TEE 签名
        signature = self.tee.sign_data(report_payload)

        final_package = {
            "report": report_payload,
            "signature": signature
        }

        print(f"✅ [TMAA] 已生成签名可信报告 (Signature: {signature[:10]}...)")
        return final_package