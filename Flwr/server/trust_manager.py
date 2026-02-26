import math

class TrustScoreManager:
    """
    TMAA 信任分管理模块 - 双流架构版
    负责评估基于机况的硬件信任分，并行史分演变。
    """
    def __init__(self, alpha=3.0, beta=1.0, gamma=0.5):
        # 权重计算阶段的超参数
        self.alpha = alpha  # 安全因子门控强度 (针对 TrustScore)
        self.beta = beta    # 绩效因子线型强度 (针对 ContentScore)
        self.gamma = gamma  # 历史因子的平滑惯性 (针对 HistPerf)
        
        self.history = {}  # client_id -> { "ema_score": float, "rounds": int }
        self.ema_decay = 0.7  # 历史分数的遗忘因子 (beta)

    def evaluate_m_attest_and_trust(self, client_id: str, report: dict) -> tuple:
        """计算 M_attest 并基于客户端遥测给出当前状态机况评估 (TrustScore)。"""
        metrics = report.get("metrics", {})
        
        # --- Part A: 静态硬门禁 (M_attest) ---
        integrity = metrics.get("system_integrity", {})
        m_attest = 0.0 if integrity.get("file_tampered", False) else 1.0
        
        if m_attest == 0:
            return 0.0, 0.0
            
        # 异常检测：通过遥测指标产生 Score_anomaly
        fingerprint = metrics.get("behavior_fingerprint", {})
        gpu_vol = fingerprint.get("gpu_volatility", 0.0)
        cpu_vol = fingerprint.get("cpu_volatility", 0.0)
        
        anomaly_score = 0.0
        # 极高的波动性可能暗示进程异常
        if gpu_vol > 0.05 or cpu_vol > 0.1:
            anomaly_score = 0.5
            
        trust_score = m_attest * (1.0 - anomaly_score)
        return m_attest, trust_score

    def update_history_and_get_weight(self, 
                                      client_updates: dict, 
                                      mu_avg: float, 
                                      sigma_scale: float) -> dict:
        """
        执行 Phase 3 (权重流与历史演进)
        client_updates: { cid: {'s_content': float, 's_trust': float} }
        返回: { cid: raw_score_k }
        """
        raw_scores = {}
        for cid, data in client_updates.items():
            s_content = data['s_content']
            s_trust = data['s_trust']
            
            # 读取历史 (冷启动初始化)
            if cid not in self.history:
                hist_prev = 0.5  # 中立启动
                self.history[cid] = {"ema_score": 0.5, "rounds": 0}
            else:
                hist_prev = self.history[cid]["ema_score"]
                
            # === Stream A: 历史更新流 (相对竞争机制) ===
            z_score = (s_content - mu_avg) / sigma_scale if sigma_scale > 0 else 0.0
            update_signal = 1.0 / (1.0 + math.exp(-z_score)) # Sigmoid 竞争势
            
            # EMA 更新历史
            hist_new = self.ema_decay * hist_prev + (1 - self.ema_decay) * update_signal
            self.history[cid]["ema_score"] = hist_new
            self.history[cid]["rounds"] += 1
            
            # === Stream B: 权重计算流 ===
            # (TrustScore)^alpha * (ContentScore)^beta * (HistPerf)^gamma
            s_raw = (s_trust ** self.alpha) * (s_content ** self.beta) * (hist_prev ** self.gamma)
            raw_scores[cid] = s_raw
            
        return raw_scores
