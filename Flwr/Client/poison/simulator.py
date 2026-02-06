
import random
import math
import time
import numpy as np
from typing import List, Dict

class DeviceSimulator:
    """
    硬件行为模拟器 (Device Simulator)
    
    生成符合物理规律的"带剧情"时序数据。
    """
    
    def __init__(self, device_id: str, profile_type: str = "NVIDIA_RTX3090", is_malicious: bool = False):
        self.device_id = device_id
        self.profile_type = profile_type
        self.is_malicious = is_malicious
        
        # 1. 加载设备配置 (Static Spec)
        self.specs = self._get_specs(profile_type)
        
        # 2. 初始化状态
        self.current_temp = 40.0 # 初始温度
        self.base_latency = 20.0 if "NVIDIA" in profile_type else 80.0 # 弱设备延迟高
        
    def _get_specs(self, p_type: str) -> dict:
        """定义设备规格库"""
        specs = {
            "NVIDIA_RTX3090": {
                "cpu_cores": 16, "mem_gb": 32, "tflops": 35.6, "tee": "Intel SGX",
                "thermal_coeff": 0.5, "cooling_rate": 0.2
            },
            "Jetson_Nano": {
                "cpu_cores": 4, "mem_gb": 4, "tflops": 0.47, "tee": "TrustZone",
                "thermal_coeff": 1.2, "cooling_rate": 0.05 # 散热差
            },
            "Raspberry_Pi_4": {
                "cpu_cores": 4, "mem_gb": 2, "tflops": 0.1, "tee": "None",
                "thermal_coeff": 1.5, "cooling_rate": 0.03
            }
        }
        return specs.get(p_type, specs["NVIDIA_RTX3090"])
        
    def generate_trace(self, start_time: float, duration_sec: int, pattern: str = "sawtooth") -> List[Dict]:
        """
        生成一段时序数据
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
                # 懒惰节点: 几乎不工作
                phase = "Idle"
                cpu = random.uniform(0, 5)
                gpu = random.uniform(0, 2)
                power_load = 0.05
                
            elif self.is_malicious and pattern == "miner":
                # 挖矿节点: 一直满载
                phase = "Mining"
                cpu = random.uniform(90, 100)
                gpu = random.uniform(95, 100)
                power_load = 1.0
                
            else:
                # 正常节点: 周期性训练 (Sawtooth Wave)
                cycle_pos = (t % cycle_len) / cycle_len
                
                if cycle_pos < 0.2:
                    phase = "Data_Loading"
                    cpu = random.uniform(60, 80)
                    gpu = random.uniform(10, 30)
                    power_load = 0.4
                elif cycle_pos < 0.6:
                    phase = "Forward"
                    cpu = random.uniform(30, 50)
                    gpu = random.uniform(70, 90)
                    power_load = 0.8
                elif cycle_pos < 0.9:
                    phase = "Backward" # 计算量最大
                    cpu = random.uniform(40, 60)
                    gpu = random.uniform(90, 100)
                    power_load = 1.0
                else:
                    phase = "Idle" # Batch 间隙
                    cpu = random.uniform(5, 15)
                    gpu = random.uniform(0, 5)
                    power_load = 0.1
            
            # 3. 物理一致性模拟 (温度与风扇)
            # 温度滞后于负载 (EMA)
            target_temp = 35.0 + (50.0 * power_load) # 满载 85度，空载 35度
            # T_new = T_old + (Target - T_old) * Coeff
            self.current_temp += (target_temp - self.current_temp) * 0.1 * self.specs["thermal_coeff"]
            # 添加随机波动
            self.current_temp += random.gauss(0, 0.5)
            
            # 风扇转速随温度变化
            fan_speed = int(min(3000, max(800, (self.current_temp - 40) * 60)))
            
            # 4. 网络抖动模拟 (Poisson 长尾)
            latency = self.base_latency + random.gauss(0, 5)
            if random.random() < 0.05: # 5% 概率发生网络拥塞
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
        return {
            "device_id": self.device_id,
            "hardware_type": self.profile_type,
            "cpu_cores": self.specs["cpu_cores"],
            "total_memory_gb": self.specs["mem_gb"],
            "tflops": self.specs["tflops"],
            "tee_type": self.specs["tee"],
            "is_malicious": self.is_malicious
        }
