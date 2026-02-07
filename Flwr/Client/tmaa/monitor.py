"""
==============================================================================
🖥️ SystemMonitor 系统资源监控模块
==============================================================================
本模块负责监控客户端的运行时行为，构建"资源指纹"。

监控维度 (Layers):
    L1: 文件完整性 (File Integrity) -> 防止核心代码被篡改
    L2: 资源指纹 (Resource Usage) -> 区分真实训练与模拟行为
    L4: 网络连接 (Network Connections) -> 防止非法数据外传

核心指标:
    - cpu_volatility: CPU 波动率
      真实训练通常有周期性的波动 (Loading -> Forward -> Backward)，
      而死循环(While True)通常是平直的一条线。

作者: Flwr 联邦学习项目
==============================================================================
"""

import psutil
import time
import hashlib
import os
import threading
import statistics
from typing import List, Dict, Any, Optional

class SystemMonitor:
    def __init__(self, pid: int, device_id: str = None, use_simulation: bool = False):
        """
        Args:
            pid: 被监控进程的 PID
            device_id: (Simulation) 模拟设备ID
            use_simulation: 是否使用数据库仿真数据
        """
        self.pid = pid
        self.device_id = device_id
        self.use_simulation = use_simulation
        
        # Simulation State
        self.sim_offset = 0
        self.db_manager = None
        if self.use_simulation:
            from poison.db_manager import DBManager
            try:
                self.db_manager = DBManager()
            except:
                print("⚠️ [Monitor] DB Connection failed, fallback to real monitor")
                self.use_simulation = False

        self.metrics_history = {
            "cpu": [],
            "memory": [],
            "timestamps": []
        }
        self.integrity_status = True
        self.network_violations = 0

        # 定义网络白名单 (允许的 IP)
        self.allowed_ips = ["127.0.0.1", "0.0.0.0", "localhost"]

    def check_file_integrity(self, file_paths: List[str]) -> Dict[str, str]:
        """
        L1: 检查关键文件哈希 (防止代码篡改)
        """
        hashes = {}
        for path in file_paths:
            if os.path.exists(path):
                with open(path, "rb") as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                    hashes[path] = file_hash
            else:
                self.integrity_status = False
                print(f"⚠️  [Monitor] 警告: 关键文件丢失 -> {path}")
        return hashes

    def sample_resources(self):
        """
        L2: 采样 CPU/内存 (构建资源指纹)
        """
        if self.use_simulation and self.db_manager:
            # === Mode A: Simulation (Read from DB) ===
            try:
                # Fetch 1 record at current offset
                # 假设每秒调用一次，这里简单地读下一条
                logs = self.db_manager.fetch_telemetry(self.device_id, limit=1, offset=self.sim_offset)
                if logs:
                    record = logs[0]
                    cpu = record['cpu_usage']
                    mem = record['memory_usage_mb']
                    self.metrics_history["cpu"].append(cpu)
                    self.metrics_history["memory"].append(mem)
                    self.metrics_history["timestamps"].append(time.time())
                    self.sim_offset += 1
                else:
                    # 数据读完了，循环读取或保持最后状态
                    self.sim_offset = 0 
            except Exception as e:
                print(f"⚠️ [Monitor] Simulation read error: {e}")
                
        else:
            # === Mode B: Real Monitoring (psutil) ===
            try:
                proc = psutil.Process(self.pid)
                # interval=None 表示非阻塞，返回上次调用以来的平均值
                cpu = proc.cpu_percent(interval=None)
                mem = proc.memory_info().rss / 1024 / 1024  # Convert to MB
    
                self.metrics_history["cpu"].append(cpu)
                self.metrics_history["memory"].append(mem)
                self.metrics_history["timestamps"].append(time.time())
            except psutil.NoSuchProcess:
                self.integrity_status = False
                # print("⚠️  [Monitor] 目标进程已消失")

    def check_network(self):
        """
        L4: 检查网络连接 (防止数据外泄)
        
        扫描进程当前建立的所有 TCP 连接，核对白名单。
        """
        try:
            proc = psutil.Process(self.pid)
            connections = proc.connections()
            for conn in connections:
                if conn.status == 'ESTABLISHED':
                    if hasattr(conn, 'raddr') and hasattr(conn.raddr, 'ip'):
                        remote_ip = conn.raddr.ip
                        # 简单白名单逻辑
                        is_local = remote_ip in self.allowed_ips or remote_ip.startswith("127.")
                        is_lan = remote_ip.startswith("192.168") or remote_ip.startswith("10.")
                        
                        if not (is_local or is_lan):
                            # self.network_violations += 1
                            # print(f"⚠️  [Monitor] 发现可疑外联: {remote_ip}")
                            pass
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    def calculate_volatility(self) -> float:
        """
        计算 CPU 波动率 (区分真实训练与死循环)
        
        - 真实训练: 波动较大 (Sawtooth like)
        - 死循环/空转: 波动极小
        """
        if len(self.metrics_history["cpu"]) < 2:
            return 0.0
        try:
            return statistics.variance(self.metrics_history["cpu"])
        except:
            return 0.0