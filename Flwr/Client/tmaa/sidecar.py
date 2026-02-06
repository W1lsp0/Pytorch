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
        """触发 L3 数据审计"""
        # 实例化 Inspector (若未传入 device 则默认 cpu)
        target_device = device if device else "cpu"
        inspector = DataInspector(target_device)
        
        # 执行全量审计
        if net:
            # 返回完整的 metrics 字典 (包括 initial_loss 等)
            self.data_metrics = inspector.inspect(net, dataloader)
        else:
            # 如果没有 net (极少情况)，只能做基础统计
            # 这里简单处理，或者要求 net 必须存在
            print("⚠️ [TMAA] Warning: No net provided for inspection.")
            self.data_metrics = {}

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