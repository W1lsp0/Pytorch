import os
import json
from datetime import datetime

class AuditLogger:
    """
    TMAA 审计日志记录器
    
    职责:
    1. 记录服务器端的全局审计日志 (tmaa_server_audit.log)
    2. 记录特定高风险客户端的详细审计轨迹 (client_0_audit.jsonl)
    """
    
    def __init__(self, log_dir: str = "log"):
        self.log_dir = log_dir
        # Ensure log directory exists
        os.makedirs(self.log_dir, exist_ok=True)
        self.main_log_path = os.path.join(self.log_dir, "tmaa_server_audit.log")
        
    def log(self, message: str):
        """
        写入主审计日志并打印到控制台
        """
        print(message, flush=True)
        with open(self.main_log_path, "a", encoding="utf-8") as f:
            f.write(message + "\n")

    def log_client_event(self, client_cid: str, tee_id: str, server_round: int, report: dict):
        """
        记录特定客户端的详细事件 (用于深入审计)
        目前专门针对 Client 0 (worker_0000)
        """
        # 识别 Client 0 (Client ID=0 -> worker_0000)
        if "worker_0000" in tee_id or str(client_cid) == "0":
            audit_entry = {
                "round": server_round,
                "timestamp": datetime.now().isoformat(),
                "report": report
            }
            
            client0_log_path = os.path.join(self.log_dir, "client_0_audit.jsonl")
            
            # 使用 JSON Lines 格式追加
            with open(client0_log_path, "a", encoding="utf-8") as f0:
                f0.write(json.dumps(audit_entry, ensure_ascii=False) + "\n")
