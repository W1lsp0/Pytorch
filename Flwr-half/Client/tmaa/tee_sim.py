"""
==============================================================================
🔑 Simulated TEE 硬件可信根模拟
==============================================================================
本模块模拟 TEE (Trusted Execution Environment) 硬件功能。
如 Intel SGX, TDX 或 ARM TrustZone。

核心能力:
    1. 硬件身份标识 (Device ID)
    2. 安全签名能力 (Hardware Signing)
    3. 远程证明 (Remote Attestation - 简化模拟)

注意:
    这是一个纯软件模拟器。真实场景中，私钥被烧录在硬件熔丝或安全区域中，
    OS 无法直接读取，只能通过指令请求签名。

作者: Flwr 联邦学习项目
==============================================================================
"""

import json
import hashlib
from datetime import datetime

class SimulatedTEE:
    """
    模拟 TEE 硬件环境，提供不可伪造的签名服务。
    """

    def __init__(self, device_id="simulated_device_001"):
        self.device_id = device_id
        # 模拟不可导出的硬件私钥 (Hardware Secret)
        # 只要这个 key 不泄露，签名即不可伪造
        self._private_key_secret = f"hw_secret_key_for_{device_id}_@!#"

    def sign_data(self, data_dict: dict) -> str:
        """
        对数据进行硬件签名 (Hardware Signing)
        
        Args:
            data_dict: 待签名的数据字典
            
        Returns:
            str: 签名哈希值 (Hex)
        """
        # 1. 序列化数据 (sort_keys=True 保证字段顺序一致性)
        payload = json.dumps(data_dict, sort_keys=True)

        # 2. 模拟签名: Ensure(Payload + Secret)
        # 在真实场景中，这里会调用 TPM/Enclave 指令使用 RSA/ECDSA 私钥签名
        signature_content = f"{payload}{self._private_key_secret}"
        signature = hashlib.sha256(signature_content.encode()).hexdigest()

        return signature

    def get_attestation_report(self):
        """
        获取硬件远程证明报告 (Remote Attestation)
        证明当前环境确实运行在受保护的 TEE 中。
        """
        return {
            "device_id": self.device_id,
            "tee_type": "Simulated_v1.0",
            "fw_version": "1.0.2",
            "secure_boot": True,
            "timestamp": datetime.now().isoformat()
        }