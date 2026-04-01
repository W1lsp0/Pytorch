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
    
    def __init__(self, device_id: str, profile_type: str = "NVIDIA_RTX3090", is_malicious: bool = False, pattern: str = "normal"):
        """
        初始化模拟器

        Args:
            device_id: 设备唯一ID
            profile_type: 硬件配置预设名称 (如 "NVIDIA_RTX4090")
            is_malicious: 是否为恶意节点
            pattern: 行为模式 ('normal', 'lazy', 'miner')
        """
        self.device_id = device_id
        self.profile_type = profile_type
        self.is_malicious = is_malicious
        self.pattern = pattern
        
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

    def generate_phase_data(self, phase: str, count: int, start_step: int = 0, complexity: str = "high") -> List[Dict]:
        """
        生成特定阶段的离散遥测数据池 (Data Pool)
        
        Args:
            phase: 阶段名称 (Idle, Loading, Forward, Backward)
            count: 生成数量
            start_step: 起始步数 (用于数据库排序)
            complexity: 数据复杂度 ('high'=[IID/Compute-Bound], 'low'=[Non-IID/IO-Bound])
            
        Returns:
            List[Dict]: 遥测数据列表
        """
        trace = []
        
        # 定义阶段特征 (CPU, GPU, Power)
        # 恶意模式下的特殊行为 (Lazy, Miner) 会覆盖这些
        if self.is_malicious and self.pattern == "lazy":
             base_cpu, base_gpu, power = (5, 0, 0.1)
        elif self.is_malicious and self.pattern == "miner":
             base_cpu, base_gpu, power = (95, 100, 1.0)
        else:
            # 正常训练特征
            if phase == "Idle":
                base_cpu, base_gpu, power = (10, 0, 0.1)
            elif phase == "Loading":  # IO 密集
                base_cpu, base_gpu, power = (70, 10, 0.3)
            elif phase == "Forward":  # 计算密集 (中)
                base_cpu, base_gpu, power = (40, 80, 0.7)
            elif phase == "Backward": # 计算密集 (高)
                base_cpu, base_gpu, power = (50, 95, 1.0)
            else:
                base_cpu, base_gpu, power = (10, 0, 0.1)

        # [Virtual-Reality Alignment] 虚实对齐逻辑
        # Low Complexity (Non-IID) -> IO Bound -> Higher Jitter
        # High Complexity (IID) -> Compute Bound -> Lower Jitter
        if complexity == "low":
            jitter_factor = 3.0  # 剧烈抖动 (IO等待)
        else:
            jitter_factor = 1.0  # 平滑计算

        for i in range(count):
            step = start_step + i
            
            # 1. 波动模拟 (引入 Jitter Factor)
            cpu = base_cpu + random.uniform(-5 * jitter_factor, 5 * jitter_factor)
            gpu = base_gpu + random.uniform(-5 * jitter_factor, 5 * jitter_factor)
            
            # 裁剪范围
            cpu = max(0, min(100, cpu))
            gpu = max(0, min(100, gpu))
            
            # 2. 物理一致性 (温度)
            # 目标温度 = 环境(35) + 负载增温(50 * power)
            target_temp = 35.0 + (50.0 * power)
            delta = (target_temp - self.current_temp) * 0.1 * self.specs["thermal_coeff"]
            self.current_temp += delta + random.gauss(0, 0.2)
            
            # 3. 风扇
            fan_speed = int(min(3000, max(800, (self.current_temp - 40) * 60)))
            
            # 4. 延迟 (简单模拟)
            latency = self.base_latency + random.gauss(0, 2)

            record = {
                "device_id": self.device_id,
                "step": step,           # [New] 逻辑步数
                "phase": phase,         # [New] 阶段标签
                "cpu_usage": round(cpu, 2),
                "memory_usage_mb": self.specs["mem_gb"] * 1024 * (0.2 + 0.3 * power),
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
