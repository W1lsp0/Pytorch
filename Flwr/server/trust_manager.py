import math

class TrustScoreManager:
    """
    TMAA 信任分管理模块 - 双流架构版
    负责评估基于机况的硬件信任分，进行历史分演变。
    """
    def __init__(self, alpha=3.0, beta=1.0, gamma=0.5):
        # 权重计算阶段的超参数
        self.alpha = alpha  # 安全因子门控强度 (针对 TrustScore)
        self.beta = beta    # 绩效因子线型强度 (针对 ContentScore)
        self.gamma = gamma  # 历史因子的平滑惯性 (针对 HistPerf)
        
        self.history = {}  # client_id -> { "ema_score": float, "rounds": int }
        self.ema_decay = 0.7  # 历史分数的遗忘因子 (beta)
        
        # 异常衰减控制参数
        self.lambda_penalty = 5.0
        self.tau_tolerance = 0.1
        self.rho_exponent = 2.0

    def evaluate_device_integrity(self, client_id: str, report: dict) -> tuple:
        """计算 M_attest 并基于客户端遥测给出当前状态机况评估 (TrustScore)。"""
        metrics = report.get("metrics", {})
        
        # --- Part A: 静态硬门禁 (M_attest) ---
        integrity = metrics.get("system_integrity", {})
        m_attest = 0.0 if integrity.get("file_tampered", False) else 1.0
        
        if m_attest == 0:
            return 0.0, 0.0
            
        # --- Part B: 动态软感知 (Anomaly Score) ---
        fingerprint = metrics.get("behavior_fingerprint", {})
        throughput_check = fingerprint.get("throughput_check", "NORMAL")
        
        # 提取异常信号作为 A_k (Anomaly Score)
        # 实际情况中，这里可以是隔离森林模型的输出
        # 这里为了简化，构造一个标量异常分数
        a_k = 0.0
        gpu_vol = fingerprint.get("gpu_volatility", 0.0)
        cpu_vol = fingerprint.get("cpu_volatility", 0.0)
        
        # 异常的平滑直线的波动率接近于0
        if gpu_vol < 1.0 and cpu_vol < 1.0:
            a_k += 0.4
            
        if "SUSPECTED_FAKE" in throughput_check:
            a_k += 0.6
            
        # 指数衰减惩罚
        penalty = math.exp(-self.lambda_penalty * (max(0, a_k - self.tau_tolerance) ** self.rho_exponent))
        
        trust_score = m_attest * penalty
        return m_attest, trust_score

    def fetch_history(self, client_id: str) -> float:
        """获取节点的历史信誉得分，如果尚未建立档案，则返回冷启动的 0.5"""
        if client_id not in self.history:
            return 0.5
        return self.history[client_id]["ema_score"]

    def update_history(self, client_updates: dict, mu_avg: float, sigma_scale: float):
        """
        执行 Stream A (保留历史表现的纯净性)
        基于本轮的内容实力 (S_content) 更新 HistPerf 的 EMA 参数
        client_updates: dict, {cid: s_content}
        """
        for cid, s_content in client_updates.items():
            if cid not in self.history:
                self.history[cid] = {"ema_score": 0.5, "rounds": 0}
            
            hist_prev = self.history[cid]["ema_score"]
            
            # 引入竞争机制的 Tanh (Sigmoid变体)
            z_score = (s_content - mu_avg) / sigma_scale if sigma_scale > 0 else 0.0
            # 使用标准的 Sigmoid 函数将差异映射到 0~1 的更新信号
            update_signal = 1.0 / (1.0 + math.exp(-z_score)) 
            
            # EMA 更新历史
            hist_new = self.ema_decay * hist_prev + (1 - self.ema_decay) * update_signal
            self.history[cid]["ema_score"] = hist_new
            self.history[cid]["rounds"] += 1

    def calculate_raw_score(self, client_id: str, trust_score: float, content_score: float) -> float:
        """
        执行 Stream B (生成加权基底分数)
        基于 Trust, Content 和 History 计算 RawScore
        """
        hist_perf = self.fetch_history(client_id)
        # Raw = Trust^alpha * Content^beta * History^gamma
        raw_score = (trust_score ** self.alpha) * (content_score ** self.beta) * (hist_perf ** self.gamma)
        return raw_score