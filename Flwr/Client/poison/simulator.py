"""
==============================================================================
🎮 Device Simulator 硬件行为模拟器
==============================================================================
本模块模拟真实的异构设备行为，生成符合物理规律的"带剧情"时序数据。

核心功能:
    1. 异构设备规格库 (从嵌入式树莓派到数据中心 A100)
    2. 物理一致性模拟 (热力学、风扇响应)
    3. 训练负载模拟 (Sawtooth 波形)
    4. 恶意行为模拟 (懒惰节点、挖矿劫持)

物理模型:
    - 温度模型: 使用指数移动平均 (EMA) 模拟热惯性
    - 性能模型: 根据 TFLOPS 计算训练周期长度
    - 网络模型: 模拟泊松分布的长尾延迟和丢包抖动

作者: Flwr 联邦学习项目
==============================================================================
"""

import random
import math
import time
import numpy as np
from typing import List, Dict, Optional

def cast_type(t): return t if t else ""

class DeviceSimulator:
    """
    硬件行为模拟器 (Device Simulator)
    
    生成符合物理规律的"带剧情"时序数据。
    """
    
    def __init__(self, device_id: str, profile_type: str = "NVIDIA_RTX3090", is_malicious: bool = False):
        """
        初始化模拟器

        Args:
            device_id: 设备唯一ID
            profile_type: 硬件配置预设名称 (如 "NVIDIA_RTX4090")
            is_malicious: 是否为恶意节点
        """
        self.device_id = device_id
        self.profile_type = profile_type
        self.is_malicious = is_malicious
        
        # 1. 加载设备配置
        # 如果传入的类型不在定义中，默认 fallback 到 RTX3090
        self.specs = self._get_specs(profile_type)
        if not self.specs:
            self.specs = self._get_specs("NVIDIA_RTX3090")
            print(f"⚠️  未知设备类型 '{profile_type}'，降级为 RTX3090")
        
        # 2. 初始化热力学状态
        self.current_temp = 40.0 # 初始温度
        # 根据品牌推断基础延迟 (N 卡通常有更好的 IB/RDMA 支持假设; 树莓派等更慢)
        self.base_latency = 20.0 if "NVIDIA" in cast_type(profile_type) else 80.0 
        
    def _get_specs(self, p_type: str) -> dict:
        """
        定义丰富多样的设备规格库 (半精度 TFLOPs)
        涵盖: 数据中心卡(A100), 消费级卡(4090), 边缘设备(Jetson), CPU节点
        
        参数说明:
            - tflops: 算力 (影响训练周期长短)
            - thermal_coeff: 热系数 (值越大，升温越快，散热越差)
            - tee: 可信执行环境类型
        """
        specs_db = {
            # === 数据中心级 (Datacenter) ===
            "NVIDIA_A100_80GB": {"cpu_cores": 64, "mem_gb": 80.0, "tflops": 312.0, "tee": "Intel TDX", "thermal_coeff": 0.3},
            "NVIDIA_V100_32GB": {"cpu_cores": 40, "mem_gb": 32.0, "tflops": 125.0, "tee": "None",      "thermal_coeff": 0.4},
            "NVIDIA_T4":       {"cpu_cores": 16, "mem_gb": 16.0, "tflops": 65.0,  "tee": "None",      "thermal_coeff": 0.6},
            
            # === 消费级高端 (Consumer High-End) ===
            "NVIDIA_RTX4090":  {"cpu_cores": 32, "mem_gb": 24.0, "tflops": 82.6,  "tee": "None",      "thermal_coeff": 0.5},
            "NVIDIA_RTX3090":  {"cpu_cores": 24, "mem_gb": 24.0, "tflops": 35.6,  "tee": "None",      "thermal_coeff": 0.5},
            "NVIDIA_RTX3080":  {"cpu_cores": 20, "mem_gb": 10.0, "tflops": 29.8,  "tee": "None",      "thermal_coeff": 0.6},
            
            # === 边缘计算 (Edge AI) ===
            "NVIDIA_Jetson_AGX": {"cpu_cores": 8, "mem_gb": 32.0, "tflops": 11.0,  "tee": "TrustZone", "thermal_coeff": 0.9},
            "NVIDIA_Jetson_NX":  {"cpu_cores": 6, "mem_gb": 8.0,  "tflops": 6.0,   "tee": "TrustZone", "thermal_coeff": 1.0},
            "NVIDIA_Jetson_Nano": {"cpu_cores": 4,"mem_gb": 4.0,  "tflops": 0.47,  "tee": "TrustZone", "thermal_coeff": 1.2},
            
            # === 低功耗/IoT (IoT) ===
            "Raspberry_Pi_4":    {"cpu_cores": 4, "mem_gb": 4.0,  "tflops": 0.05,  "tee": "None",      "thermal_coeff": 1.5},
            "Intel_NUC":         {"cpu_cores": 8, "mem_gb": 16.0, "tflops": 0.2,   "tee": "SGX",       "thermal_coeff": 0.8}
        }
        return specs_db.get(p_type, None)

    def generate_trace(self, start_time: float, duration_sec: int, pattern: str = "sawtooth") -> List[Dict]:
        """
        生成一段连续的时序遥测数据
        
        Args:
            start_time: 起始时间戳
            duration_sec: 持续时长(秒)
            pattern: 行为模式 ('sawtooth', 'lazy', 'miner')
            
        Returns:
            List[Dict]: 遥测数据记录列表
        """
        trace = []
        time_step = 1.0 # 采样间隔 1秒
        
        # 训练过程模拟: Loading -> Forward -> Backward -> Idle
        # 周期长度 (秒) = 基准 / TFLOPs (算力越弱，周期越长)
        # 假设基准周期 5秒 (RTX3090)
        cycle_len = max(2.0, 5.0 * (35.6 / self.specs["tflops"])) 
        
        for t in range(int(duration_sec)):
            now = start_time + t
            
            if self.is_malicious and pattern == "lazy":
                # [恶意模式] 懒惰节点: 伪装在线但不干活
                phase = "Idle"
                cpu = random.uniform(0, 5)
                gpu = random.uniform(0, 2)
                power_load = 0.05
                
            elif self.is_malicious and pattern == "miner":
                # [恶意模式] 挖矿劫持: 一直满载计算哈希
                phase = "Mining"
                cpu = random.uniform(90, 100)
                gpu = random.uniform(95, 100)
                power_load = 1.0
                
            else:
                # [正常模式] 周期性训练 (Sawtooth Wave)
                cycle_pos = (t % cycle_len) / cycle_len
                
                if cycle_pos < 0.2:
                    phase = "Data_Loading"     # 数据加载: 高CPU, 低GPU, 中能耗
                    cpu = random.uniform(60, 80)
                    gpu = random.uniform(10, 30)
                    power_load = 0.4
                elif cycle_pos < 0.6:
                    phase = "Forward"          # 前向传播: 中CPU, 高GPU
                    cpu = random.uniform(30, 50)
                    gpu = random.uniform(70, 90)
                    power_load = 0.8
                elif cycle_pos < 0.9:
                    phase = "Backward"         # 反向传播: 计算密集型, 满载
                    cpu = random.uniform(40, 60)
                    gpu = random.uniform(90, 100)
                    power_load = 1.0
                else:
                    phase = "Idle"             # Batch 间隙
                    cpu = random.uniform(5, 15)
                    gpu = random.uniform(0, 5)
                    power_load = 0.1
            
            # --- 物理一致性模拟 (Physics Simulation) ---
            
            # 1. 温度模型
            # 目标温度 = 环境温度(35) + 负载增温(50 * load) -> 满载85度
            target_temp = 35.0 + (50.0 * power_load)
            
            # 使用差分方程模拟热惯性 (牛顿冷却定律变体)
            # T_new = T_old + (Target - T_old) * Coeff
            delta = (target_temp - self.current_temp) * 0.1 * self.specs["thermal_coeff"]
            self.current_temp += delta
            # 添加随机热噪声
            self.current_temp += random.gauss(0, 0.5)
            
            # 2. 风扇转速模型
            # 简单的线性反馈控制: (Temp - 40) * 60
            # 限制在 800 ~ 3000 RPM
            fan_speed = int(min(3000, max(800, (self.current_temp - 40) * 60)))
            
            # 3. 网络延迟模拟
            # 基础延迟 + 抖动
            latency = self.base_latency + random.gauss(0, 5)
            # 模拟偶尔的网络拥塞 (长尾分布)
            if random.random() < 0.05: # 5% 概率发生拥塞
                latency += random.uniform(200, 1000)
            
            record = {
                "device_id": self.device_id,
                "timestamp": now,
                "phase": phase,
                "cpu_usage": round(cpu, 2),
                "memory_usage_mb": self.specs["mem_gb"] * 1024 * (0.2 + 0.5 * power_load),
                "gpu_util": round(gpu, 2),
                "temperature_c": round(self.current_temp, 1),
                "fan_speed_rpm": fan_speed,
                "latency_ms": round(latency, 2)
            }
            trace.append(record)
            
        return trace

    def get_profile(self) -> dict:
        """获取设备静态画像"""
        return {
            "device_id": self.device_id,
            "hardware_type": self.profile_type,
            "cpu_cores": self.specs["cpu_cores"],
            "total_memory_gb": self.specs["mem_gb"],
            "tflops": self.specs["tflops"],
            "tee_type": self.specs["tee"],
            "is_malicious": self.is_malicious
        }
