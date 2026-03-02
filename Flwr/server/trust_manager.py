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

import os
import json
import math
import mysql.connector
from typing import Dict, Tuple, List


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

        # ---- 历史信誉持久化存储 (MySQL) ----
        self.db_config = {
            'host': "59.67.152.211",
            'port': 3306,
            'user': "root",
            'password': "root123456",
            'database': "tmaa_simulation",
            'raise_on_warnings': False
        }
        # 结构: { client_id: {"ema_score": float, "rounds": int} }
        self.history: Dict[str, dict] = {}

        # ---- EMA 衰减系数 ----
        # 0.7 表示 70% 继承历史口碑，30% 吸收本轮竞争信号
        self.ema_decay = 0.7

        # ---- 黑名单与淘汰超参数 ----
        self.prune_threshold = 0.1  # τ: 死亡线，跌破此值永久封禁
        self.blacklist = set()

        # ---- 指数衰减惩罚超参数 ----
        self.lambda_penalty = 5.0   # λ: 惩罚强度系数
        self.tau_tolerance = 0.1    # τ: 容忍基线（低于此值的异常不惩罚）
        self.rho_exponent = 2.0     # ρ: 断崖指数（≥2 时形成几何级惩罚）

        # ---- 从本地恢复历史状态 ----
        self._load_state()

    def _get_connection(self):
        """获取 MySQL 数据库连接"""
        return mysql.connector.connect(**self.db_config)

    def _init_db(self) -> None:
        """初始化 MySQL 数据库表结构"""
        try:
            # 先连 Server，确保 Database 存在
            init_cfg = self.db_config.copy()
            del init_cfg['database']
            cnx = mysql.connector.connect(**init_cfg)
            cursor = cnx.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.db_config['database']}")
            cursor.close()
            cnx.close()
            
            # 再连 Database 建表
            cnx = self._get_connection()
            cursor = cnx.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS server_history_pool (
                    client_id VARCHAR(50) PRIMARY KEY,
                    ema_score FLOAT NOT NULL,
                    rounds INT NOT NULL
                ) ENGINE=InnoDB COMMENT='服务端信誉池';
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS server_blacklist (
                    client_id VARCHAR(50) PRIMARY KEY,
                    reason VARCHAR(255)
                ) ENGINE=InnoDB COMMENT='服务端封禁名单';
            ''')
            cnx.commit()
            cursor.close()
            cnx.close()
        except mysql.connector.Error as err:
            print(f"⚠️ [TrustManager] 初始化 MySQL 表结构失败: {err}")

    def _load_state(self) -> None:
        """从 MySQL 数据库加载历史信誉池和黑名单"""
        self._init_db()
        try:
            cnx = self._get_connection()
            cursor = cnx.cursor(dictionary=True)
            
            # 加载 history
            cursor.execute("SELECT client_id, ema_score, rounds FROM server_history_pool")
            for row in cursor.fetchall():
                self.history[row['client_id']] = {"ema_score": row['ema_score'], "rounds": row['rounds']}
            
            # 加载 blacklist
            cursor.execute("SELECT client_id FROM server_blacklist")
            for row in cursor.fetchall():
                self.blacklist.add(row['client_id'])
                
            cursor.close()
            cnx.close()
        except Exception as e:
            print(f"⚠️ [TrustManager] 读取 MySQL 失败: {e}，将使用内存空状态。")
            self.history = {}
            self.blacklist = set()

    def _save_state(self) -> None:
        """将当前历史信誉池和黑名单持久化到 MySQL 数据库中"""
        try:
            cnx = self._get_connection()
            cursor = cnx.cursor()
            
            # 更新 history (使用 ON DUPLICATE KEY UPDATE)
            history_data = [
                (cid, data["ema_score"], data["rounds"]) 
                for cid, data in self.history.items()
            ]
            if history_data:
                cursor.executemany(
                    """
                    INSERT INTO server_history_pool (client_id, ema_score, rounds) 
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    ema_score=VALUES(ema_score), rounds=VALUES(rounds)
                    """, 
                    history_data
                )
            
            # 更新 blacklist (仅插入防重复)
            blacklist_data = [(cid, "pruned_by_low_score") for cid in self.blacklist]
            if blacklist_data:
                cursor.executemany(
                    """
                    INSERT IGNORE INTO server_blacklist (client_id, reason) 
                    VALUES (%s, %s)
                    """, 
                    blacklist_data
                )
            
            cnx.commit()
            cursor.close()
            cnx.close()
        except Exception as e:
            print(f"⚠️ [TrustManager] 写入 MySQL 失败: {e}")

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

        如果节点在黑名单中，将提前在 Strategy 拦截。此处的 fetch 仅作调用防御。
        对于首轮冷启动节点，返回中立偏下的 0.5（预热期保护）。

        参数:
            client_id: 客户端标识符

        返回:
            HistPerf 信誉分 ∈ [0, 1]
        """
        if client_id in self.blacklist:
            return 0.0

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

            # 步骤 4: 动态熔断判定（Pruning）
            if hist_new < self.prune_threshold:
                self.blacklist.add(cid)

        # 全局状态持久化落盘
        self._save_state()

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
            - 使用上一轮的 HistPerf_k(t-1) 作为资历加成，不包含本轮新表现
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