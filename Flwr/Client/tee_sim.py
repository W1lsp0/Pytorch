# client/tee_sim.py (硬件可信根模拟)
import json
import hashlib
from datetime import datetime


class SimulatedTEE:
    """
    模拟 TEE 硬件环境，提供不可伪造的签名服务。
    """

    def __init__(self, device_id="simulated_device"):
        self.device_id = device_id
        # 模拟不可导出的硬件私钥 (这里仅用简单的哈希模拟签名过程)
        self._private_key_secret = f"hardware_secret_{device_id}"

    def sign_data(self, data_dict: dict) -> str:
        """
        对数据进行硬件签名
        """
        # 1. 序列化数据 (保证顺序一致)
        payload = json.dumps(data_dict, sort_keys=True)

        # 2. 模拟签名: Hash(Payload + Hardware_Secret)
        # 在真实场景中，这里会使用 RSA/ECDSA 私钥进行加密签名
        signature_content = f"{payload}{self._private_key_secret}"
        signature = hashlib.sha256(signature_content.encode()).hexdigest()

        return signature

    def get_attestation_report(self):
        """获取简单的硬件证明信息"""
        return {
            "device_id": self.device_id,
            "fw_version": "1.0.2",
            "secure_boot": True
        }