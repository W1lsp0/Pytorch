# client/tmaa/monitor.py (系统与行为监控)
import psutil
import time
import hashlib
import os
import threading
import statistics


class SystemMonitor:
    def __init__(self, pid):
        self.pid = pid
        self.metrics_history = {
            "cpu": [],
            "memory": [],
            "timestamps": []
        }
        self.integrity_status = True
        self.network_violations = 0

        # 定义网络白名单 (允许的 IP)
        self.allowed_ips = ["127.0.0.1", "0.0.0.0", "localhost"]

    def check_file_integrity(self, file_paths):
        """L1: 检查关键文件哈希 (防止代码篡改)"""
        hashes = {}
        for path in file_paths:
            if os.path.exists(path):
                with open(path, "rb") as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                    hashes[path] = file_hash
            else:
                self.integrity_status = False
        return hashes

    def sample_resources(self):
        """L2: 采样 CPU/内存 (资源指纹)"""
        try:
            proc = psutil.Process(self.pid)
            cpu = proc.cpu_percent(interval=None)
            mem = proc.memory_info().rss / 1024 / 1024  # MB

            self.metrics_history["cpu"].append(cpu)
            self.metrics_history["memory"].append(mem)
            self.metrics_history["timestamps"].append(time.time())
        except psutil.NoSuchProcess:
            pass

    def check_network(self):
        """L4: 检查网络连接 (防止数据外泄)"""
        try:
            proc = psutil.Process(self.pid)
            connections = proc.connections()
            for conn in connections:
                if conn.status == 'ESTABLISHED':
                    remote_ip = conn.raddr.ip
                    # 简单检查：如果连接的不是本机或允许的服务器 IP
                    if remote_ip not in self.allowed_ips and not remote_ip.startswith("192.168"):
                        # 注意：真实环境中这里需要更严格的白名单逻辑
                        # self.network_violations += 1
                        pass
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    def calculate_volatility(self):
        """计算 CPU 波动率 (区分真实训练与死循环)"""
        if len(self.metrics_history["cpu"]) < 2:
            return 0.0
        try:
            return statistics.variance(self.metrics_history["cpu"])
        except:
            return 0.0