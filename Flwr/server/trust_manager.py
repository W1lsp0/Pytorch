"""
==============================================================================
🛡️ TrustScoreManager — TMAA 信任分管理模块（双流架构版）
==============================================================================
职责：
    1. 评估客户端设备的硬件完整性（M_attest 硬门禁）
    2. 基于行为指纹计算动态异常分（指数衰减惩罚）
    3. 维护每个客户端的长期历史信誉（HistPerf，EMA 演进）
    4. 生成综合绝对评分 RawScore（三维指数乘积融合）

数学公式：
    TrustScore_k = M_attest · exp(-λ · max(0, A_k - τ)^ρ)
    HistPerf_k(t) = β · HistPerf_k(t-1) + (1-β) · Sigmoid(z_score)
    RawScore_k = TrustScore^α × ContentScore^β × HistPerf^γ

作者: Flwr 联邦学习项目
==============================================================================
"""

import math
from typing import Dict, Tuple


class TrustScoreManager:
    """
    TMAA 信任分管理器
    实现「静态硬门禁 + 动态软感知」的混合信任评估机制，
    并通过正交双流架构分离「历史更新」与「权重计算」。
    """

    def __init__(self, alpha: float = 3.0, beta: float = 1.0, gamma: float = 0.5):
        """
        初始化信任管理器。

        参数:
            alpha: TrustScore 的指数权重（安全因子门控强度，越大则低信任节点惩罚越重）
            beta:  ContentScore 的指数权重（绩效因子强度）
            gamma: HistPerf 的指数权重（历史因子平滑惯性，越小则历史影响越弱）
        """
        # ---- 加权融合超参数 ----
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma

        # ---- 历史信誉持久化存储 ----
        # 结构: { client_id: {"ema_score": float, "rounds": int} }
        self.history: Dict[str, dict] = {}

        # ---- EMA 衰减系数 ----
        # 0.7 表示 70% 继承历史口碑，30% 吸收本轮竞争信号
        self.ema_decay = 0.7

        # ---- 指数衰减惩罚超参数 ----
        self.lambda_penalty = 5.0   # λ: 惩罚强度系数
        self.tau_tolerance = 0.1    # τ: 容忍基线（低于此值的异常不惩罚）
        self.rho_exponent = 2.0     # ρ: 断崖指数（≥2 时形成几何级惩罚）

    # ==================================================================
    # 第一阶段：设备完整性评估（硬门禁 + 软感知）
    # ==================================================================
    def evaluate_device_integrity(self, client_id: str, report: dict) -> Tuple[float, float]:
        """
        评估客户端设备的可信度。

        流程：
            1. 静态硬门禁：校验 TEE 签名、代码哈希、安全版本号
            2. 动态软感知：基于行为指纹提取异常分 A_k
            3. 指数衰减映射：TrustScore = M_attest · exp(-λ·max(0, A_k-τ)^ρ)

        参数:
            client_id: 客户端标识符
            report:    客户端上传的可信度报告（含 metrics 字段）

        返回:
            (m_attest, trust_score) 元组
            - m_attest:    硬门禁结果（0.0 或 1.0）
            - trust_score: 最终信任分（0.0 ~ 1.0）
        """
        metrics = report.get("metrics", {})

        # ---- Part A: 静态硬门禁（一票否决） ----
        integrity = metrics.get("system_integrity", {})
        # 若检测到文件篡改，直接熔断
        m_attest = 0.0 if integrity.get("file_tampered", False) else 1.0

        if m_attest == 0.0:
            return 0.0, 0.0

        # ---- Part B: 动态软感知（行为指纹异常检测） ----
        fingerprint = metrics.get("behavior_fingerprint", {})
        throughput_check = fingerprint.get("throughput_check", "NORMAL")

        # 构造标量异常分 A_k ∈ [0, 1]
        # 注: 生产环境中可替换为隔离森林（Isolation Forest）模型输出
        a_k = 0.0

        gpu_vol = fingerprint.get("gpu_volatility", 0.0)
        cpu_vol = fingerprint.get("cpu_volatility", 0.0)

        # 异常波动率过低（接近恒值）可能暗示伪造训练
        if gpu_vol < 1.0 and cpu_vol < 1.0:
            a_k += 0.4

        # 吞吐量检测标记为疑似伪造
        if "SUSPECTED_FAKE" in throughput_check:
            a_k += 0.6

        # ---- 指数衰减惩罚 ----
        # 公式: penalty = exp(-λ · max(0, A_k - τ)^ρ)
        # 当 A_k 超过容忍线 τ 后，惩罚按 ρ 次方几何级暴跌
        excess = max(0.0, a_k - self.tau_tolerance)
        penalty = math.exp(-self.lambda_penalty * (excess ** self.rho_exponent))

        trust_score = m_attest * penalty
        return m_attest, trust_score

    # ==================================================================
    # 第二阶段：历史信誉管理（冷启动 + EMA 演进）
    # ==================================================================
    def fetch_history(self, client_id: str) -> float:
        """
        获取节点的历史信誉得分。

        冷启动策略：
            首次参与的新节点返回中立值 0.5（不奖不罚），
            避免新节点因缺乏历史数据而被过度惩罚或偏袒。

        参数:
            client_id: 客户端标识符

        返回:
            HistPerf 信誉分 ∈ [0, 1]
        """
        if client_id not in self.history:
            return 0.5
        return self.history[client_id]["ema_score"]

    def update_history(self, content_scores: Dict[str, float],
                       mu_avg: float, sigma_scale: float) -> None:
        """
        执行 Stream A：纯净历史信誉更新（与 RawScore 计算正交解耦）。

        算法流程：
            1. 计算 Z-Score: z = (S_content - μ_avg) / σ_scale
            2. Sigmoid 竞争映射: signal = 1 / (1 + exp(-z))
               - 表现高于平均 → signal > 0.5 → 推高信誉
               - 表现低于平均 → signal < 0.5 → 拉低信誉
            3. EMA 指数滑动平均: HistPerf = β·旧值 + (1-β)·signal

        设计要点：
            - 输入仅为纯净的 ContentScore，不混入 TrustScore
            - 防止因一时硬件故障而永久毁掉节点的长期声誉

        参数:
            content_scores: {客户端ID: S_content} 本轮各节点的内容实力分
            mu_avg:         本轮所有 S_content 的均值
            sigma_scale:    本轮所有 S_content 的标准差（+1e-6 防零除）
        """
        for cid, s_content in content_scores.items():
            # 冷启动初始化
            if cid not in self.history:
                self.history[cid] = {"ema_score": 0.5, "rounds": 0}

            hist_prev = self.history[cid]["ema_score"]

            # 步骤 1: 计算相对竞争势（Z-Score 标准化）
            if sigma_scale > 0:
                z_score = (s_content - mu_avg) / sigma_scale
            else:
                z_score = 0.0

            # 步骤 2: Sigmoid 映射到 [0, 1] 区间的更新信号
            update_signal = 1.0 / (1.0 + math.exp(-z_score))

            # 步骤 3: EMA 指数移动平均更新
            hist_new = self.ema_decay * hist_prev + (1.0 - self.ema_decay) * update_signal
            self.history[cid]["ema_score"] = hist_new
            self.history[cid]["rounds"] += 1

    # ==================================================================
    # 第三阶段：综合绝对评分生成（三维指数乘积）
    # ==================================================================
    def calculate_raw_score(self, client_id: str,
                            trust_score: float, content_score: float) -> float:
        """
        执行 Stream B：生成综合绝对评分 RawScore。

        公式:
            RawScore = (TrustScore)^α × (ContentScore)^β × (HistPerf)^γ

        设计要点：
            - 使用已更新后的 HistPerf（本轮 update_history 之后的值）
            - α=3.0 使低信任节点的 RawScore 急剧趋零（安全门控）
            - γ=0.5 使历史分的影响被开方压缩（避免老资历独大）

        参数:
            client_id:     客户端标识符
            trust_score:   本轮硬件信任分 ∈ [0, 1]
            content_score: 本轮内容实力分 ∈ [0, 1]

        返回:
            绝对综合评分 RawScore（未归一化）
        """
        hist_perf = self.fetch_history(client_id)

        raw_score = (
            (trust_score ** self.alpha) *
            (content_score ** self.beta) *
            (hist_perf ** self.gamma)
        )
        return raw_score