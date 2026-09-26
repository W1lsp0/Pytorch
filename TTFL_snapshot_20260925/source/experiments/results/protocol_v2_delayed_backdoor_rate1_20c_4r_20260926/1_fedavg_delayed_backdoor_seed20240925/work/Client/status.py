
from typing import Optional, Dict, Any
from poison.db_manager import DBManager

class StatusReporter:
    """
    负责向 Dashboard 汇报客户端状态
    """
    def __init__(self, db_manager: Optional[DBManager], client_id: int, attack_type: Optional[str]):
        self.db_manager = db_manager
        self.client_id = client_id
        self.attack_type = attack_type

    def update(self, status="Waiting", round_num="-", loss="-", asr="-"):
        """
        更新客户端状态到数据库 (供 Dashboard 实时读取)
        """
        if self.db_manager:
            try:
                data = {
                    "type": "BAD" if self.attack_type else "GOOD",
                    "attack": self.attack_type.upper() if self.attack_type else "HONEST",
                    "round": round_num,
                    "loss": loss,
                    "asr": asr,
                    "status": status
                }
                self.db_manager.update_client_status(self.client_id, data)
            except Exception as e:
                pass # 避免因数据库网络抖动导致训练中断
