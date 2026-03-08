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
import numpy as np
import mysql.connector
from typing import Dict, Tuple, Optional


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
            'host': "202.113.76.179",
            'port': 3306,
            'user': "root",
            'password': "root123456",
            'database': "tmaa_server",
            'raise_on_warnings': False
        }
        # 结构: { client_id: {"ema_score": float, "risk_ema": float, "rounds": int} }
        self.history: Dict[str, dict] = {}

        # ---- 超参数设定 ----
        self.ema_decay = 0.8        # β: EMA 平滑系数，越小对新表现越敏感
        self.lambda_penalty = 5.0   # λ: 惩罚强度系数
        
        # [Scheme K] 时间维度：存储每个客户端历史 probe_entropy 序列用于时序方差分析
        self._probe_history: Dict[str, list] = {}
        # [Scheme K] 空间维度：存储历史 spectral_score
        self._spectral_history: Dict[str, list] = {}
        self.tau_tolerance = 0.1    # τ: 容忍基线（低于此值的异常不惩罚）
        self.rho_exponent = 2.0     # ρ: 断崖指数（≥2 时形成几何级惩罚）

        # 历史更新信号：相对竞争 + 绝对下限 (调和严苛度保护偏科好人)
        self.rel_signal_weight = 0.40
        self.abs_signal_weight = 0.60
        self.abs_baseline = 0.40
        self.abs_span = 0.30

        # 两级处置阈值
        self.soft_prune_threshold = 0.26
        self.soft_prune_rounds = 5

        # 独立安全流：风险 EMA（不与 Hist/Raw 混算）
        self.risk_ema_decay = 0.85
        self.risk_report_weight = 0.30
        self.risk_grad_weight = 0.70
        self.risk_soft_threshold = 0.60
        self.risk_soft_rounds = 4
        self.risk_hard_threshold = 0.90
        self.risk_hard_rounds = 4
        self.risk_raw_attenuation_power = 1.0
        # 仅当多通道强异常同时出现时，才允许 instant_risk 直接拉满到 1.0
        self.risk_instant_confirm_threshold = 0.90
        self.risk_instant_confirm_channels = 2
        # 软隔离升级黑名单前，要求存在跨通道证据 + 持续探针异常
        self.risk_soft_blacklist_cross_floor = 0.60
        self.risk_soft_blacklist_probe_rounds = 4
        self.risk_soft_blacklist_pixel_rounds = 3
        # 低误杀加严：仅对触发器通道缩短连续告警轮数，其它通道保持不变
        self.risk_soft_blacklist_trigger_rounds = 2
        self.risk_soft_blacklist_peer_rounds = 3

        # =========== 动态平衡参数 ===========

        self.soft_blacklist_rounds = 4
        # 中等加严：Risk 软隔离持续后更快升级为黑名单
        self.risk_soft_blacklist_rounds = 6

        # ---- 黑名单 ----
        self.blacklist = set()
        self.blacklist_reason: Dict[str, str] = {}

        # ---- 从本地恢复历史状态 ----
        self._load_state()

    def _get_connection(self):
        """获取 MySQL 数据库连接"""
        return mysql.connector.connect(**self.db_config)

    @staticmethod
    def _clip01(value: float) -> float:
        return max(0.0, min(1.0, value))

    def _ensure_history_entry(
        self,
        client_id: str,
        ema_score: float = 0.5,
        rounds: int = 0,
        risk_ema: float = 0.25,
    ) -> dict:
        """确保 history 中的节点结构完整（兼容旧版本只含 ema/rounds 的记录）"""
        if client_id not in self.history:
            self.history[client_id] = {
                "ema_score": float(ema_score),
                "rounds": int(rounds),
                "soft_streak": 0,
                "soft_isolated": False,
                "risk_ema": float(risk_ema),
                "risk_soft_streak": 0,
                "risk_hard_streak": 0,
                "risk_isolated": False,
                "probe_alert_streak": 0,
                "pixel_alert_streak": 0,
                "trigger_alert_streak": 0,
                "peer_alert_streak": 0,
                "peer_risk_ema": 0.0,
                "last_peer_risk": 0.0,
                "any_soft_streak": 0,
            }
        else:
            entry = self.history[client_id]
            entry.setdefault("ema_score", float(ema_score))
            entry.setdefault("rounds", int(rounds))
            entry.setdefault("soft_streak", 0)
            entry.setdefault("soft_isolated", False)
            entry.setdefault("risk_ema", float(risk_ema))
            entry.setdefault("risk_soft_streak", 0)
            entry.setdefault("risk_hard_streak", 0)
            entry.setdefault("risk_isolated", False)
            entry.setdefault("probe_alert_streak", 0)
            entry.setdefault("pixel_alert_streak", 0)
            entry.setdefault("trigger_alert_streak", 0)
            entry.setdefault("peer_alert_streak", 0)
            entry.setdefault("peer_risk_ema", 0.0)
            entry.setdefault("last_peer_risk", 0.0)
            entry.setdefault("any_soft_streak", 0)
        return self.history[client_id]

    def _mark_blacklist(self, client_id: str, reason: str) -> None:
        self.blacklist.add(client_id)
        self.blacklist_reason[client_id] = reason
        if client_id in self.history:
            self.history[client_id]["soft_isolated"] = False
            self.history[client_id]["risk_isolated"] = False

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
                    risk_ema FLOAT NOT NULL DEFAULT 0.25,
                    rounds INT NOT NULL
                ) ENGINE=InnoDB COMMENT='服务端信誉池';
            ''')
            # 兼容旧表结构：若缺失 risk_ema 列则补齐
            cursor.execute(
                """
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA=%s AND TABLE_NAME='server_history_pool' AND COLUMN_NAME='risk_ema'
                """,
                (self.db_config["database"],),
            )
            has_risk_ema = int(cursor.fetchone()[0]) > 0
            if not has_risk_ema:
                cursor.execute(
                    "ALTER TABLE server_history_pool ADD COLUMN risk_ema FLOAT NOT NULL DEFAULT 0.25 AFTER ema_score"
                )
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
            try:
                cursor.execute("SELECT client_id, ema_score, risk_ema, rounds FROM server_history_pool")
                rows = cursor.fetchall()
            except Exception:
                cursor.execute("SELECT client_id, ema_score, rounds FROM server_history_pool")
                rows = cursor.fetchall()
                for row in rows:
                    row["risk_ema"] = 0.25
            for row in rows:
                self._ensure_history_entry(
                    row['client_id'], row['ema_score'], row['rounds'], row.get("risk_ema", 0.25)
                )
            
            # 加载 blacklist
            cursor.execute("SELECT client_id, reason FROM server_blacklist")
            for row in cursor.fetchall():
                self.blacklist.add(row['client_id'])
                self.blacklist_reason[row['client_id']] = row.get("reason") or "restored_from_db"
                
            cursor.close()
            cnx.close()
        except Exception as e:
            print(f"⚠️ [TrustManager] 读取 MySQL 失败: {e}，将使用内存空状态。")
            self.history = {}
            self.blacklist = set()
            self.blacklist_reason = {}

    def _save_state(self) -> None:
        """将当前历史信誉池和黑名单持久化到 MySQL 数据库中"""
        try:
            cnx = self._get_connection()
            cursor = cnx.cursor()
            
            # 更新 history (使用 ON DUPLICATE KEY UPDATE)
            history_data = [
                (cid, data["ema_score"], data.get("risk_ema", 0.25), data["rounds"])
                for cid, data in self.history.items()
            ]
            if history_data:
                cursor.executemany(
                    """
                    INSERT INTO server_history_pool (client_id, ema_score, risk_ema, rounds)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    ema_score=VALUES(ema_score), risk_ema=VALUES(risk_ema), rounds=VALUES(rounds)
                    """, 
                    history_data
                )
            
            # 更新 blacklist (仅插入防重复)
            blacklist_data = [
                (cid, self.blacklist_reason.get(cid, "hard_pruned"))
                for cid in self.blacklist
            ]
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


        # [Scheme C - TEE 硬件雷达直死防线] 已被证实因 DP Noise 及特征空间聚类效应失效，不再进行硬截断
        # 解析数据特征监控的硬件得分 (包含了拉普拉斯噪声的隐私保护值)
        data_health_audit = metrics.get("data_health_audit", {})
        try:
            backdoor_score = float(data_health_audit.get("backdoor_score", 0.0))
        except (TypeError, ValueError):
            backdoor_score = 0.0

        # ---- 指数衰减惩罚 ----
        # 公式: penalty = exp(-λ · max(0, A_k - τ)^ρ)
        # 当 A_k 超过容忍线 τ 后，惩罚按 ρ 次方几何级暴跌
        excess = max(0.0, a_k - self.tau_tolerance)
        penalty = math.exp(-self.lambda_penalty * (excess ** self.rho_exponent))

        trust_score = m_attest * penalty
        return m_attest, trust_score

    # ==================================================================
    # [Scheme D] 服务器验证集防御：前向推理交叉熵否决
    # ==================================================================
    def apply_proxy_loss_penalty(self, client_id: str, clean_loss: float, m_attest: float, trust_score: float) -> Tuple[float, float]:
        """
        基于服务器端的纯净小样本预测结果，对试图隐藏在特征空间内的同构后门进行最后一击。
        任何导致分类边界扭曲的后门行为，不可避免地会在纯净集上表现为暴增的 CrossEntropy Loss。
        """
        # 初始化一个针对 CIFAR-10 的安全 Loss 阈值 (例如正常情况大概是 1.0~2.0)
        # 对于剧毒模型，它的 Loss 会直接冲到 5.0 甚至 12.0 以上
        SAFE_LOSS_THRESHOLD = 3.5
        
        if clean_loss > SAFE_LOSS_THRESHOLD:
            # 记录致命的硬封禁黑名单
            self._mark_blacklist(
                client_id,
                f"clean_proxy_failure: loss={clean_loss:.4f} > {SAFE_LOSS_THRESHOLD}"
            )
            return 0.0, 0.0
            
        # 若在安全范围内，可以根据 loss 比例进行温和剥削 (例如 Loss=2.0 时打个 8 折)
        loss_penalty = min(1.0, 1.5 / max(clean_loss, 0.1))
        
        return m_attest, trust_score * loss_penalty

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

        entry = self._ensure_history_entry(client_id)
        return entry["ema_score"]

    def is_soft_isolated(self, client_id: str) -> bool:
        if client_id in self.blacklist:
            return False
        entry = self._ensure_history_entry(client_id)
        return bool(entry["soft_isolated"])

    def fetch_risk_ema(self, client_id: str) -> float:
        if client_id in self.blacklist:
            return 1.0
        entry = self._ensure_history_entry(client_id)
        return float(entry["risk_ema"])

    def is_risk_isolated(self, client_id: str) -> bool:
        if client_id in self.blacklist:
            return False
        entry = self._ensure_history_entry(client_id)
        return bool(entry["risk_isolated"])

    def get_blacklist_reason(self, client_id: str) -> str:
        return self.blacklist_reason.get(client_id, "unknown")

    @staticmethod
    def _safe_float(value, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def fetch_risk_detail(self, client_id: str) -> Dict[str, float | int | bool]:
        """返回风险侧关键状态，供策略层可疑池面板读取。"""
        if client_id in self.blacklist:
            return {
                "risk_ema": 1.0,
                "risk_soft_streak": 0,
                "risk_hard_streak": self.risk_hard_rounds,
                "risk_isolated": False,
                "peer_risk_ema": 1.0,
                "peer_alert_streak": self.risk_soft_blacklist_peer_rounds,
                "last_peer_risk": 1.0,
            }
        entry = self._ensure_history_entry(client_id)
        return {
            "risk_ema": float(entry.get("risk_ema", 0.0)),
            "risk_soft_streak": int(entry.get("risk_soft_streak", 0)),
            "risk_hard_streak": int(entry.get("risk_hard_streak", 0)),
            "risk_isolated": bool(entry.get("risk_isolated", False)),
            "peer_risk_ema": float(entry.get("peer_risk_ema", 0.0)),
            "peer_alert_streak": int(entry.get("peer_alert_streak", 0)),
            "last_peer_risk": float(entry.get("last_peer_risk", 0.0)),
        }

    def _compute_tail_risk(
        self,
        scores: Optional[Dict[str, float]],
        tail: str = "high",
        margin_mad: float = 1.0,
        scale_mad: float = 2.5,
        min_mad: float = 1e-3,
    ) -> Dict[str, float]:
        """基于 median+MAD 的稳健离群风险，返回 0~1。"""
        if not scores:
            return {}
        vals = [
            self._safe_float(v)
            for v in scores.values()
            if not math.isnan(self._safe_float(v))
        ]
        if len(vals) < 3:
            return {cid: 0.0 for cid in scores}

        med = float(np.median(vals))
        mad = float(np.median(np.abs(np.array(vals) - med)))
        mad = max(mad, min_mad)

        risk_map: Dict[str, float] = {}
        for cid, raw_v in scores.items():
            v = self._safe_float(raw_v)
            if tail == "high":
                delta = v - (med + margin_mad * mad)
            else:
                delta = (med - margin_mad * mad) - v
            risk_map[cid] = self._clip01(delta / (scale_mad * mad))
        return risk_map

    def compute_report_risk(self, report: dict) -> float:
        """
        从客户端可信报告中提取当轮风险分 (0~1)。
        仅使用服务端可见字段，不依赖任何本地攻击评估指标。
        """
        metrics = report.get("metrics", {})
        data_audit = metrics.get("data_health_audit", {})
        fingerprint = metrics.get("behavior_fingerprint", {})

        backdoor_score = self._clip01(self._safe_float(data_audit.get("backdoor_score", 0.0)))
        # Loss naturally hits 3.5+ for Non-IID and 2.5 for Backdoor. Using it mathematically inverted the risk,
        # so we ignore loss_risk for Trust/Risk Isolation purposes to protect Non-IID nodes.
        
        # Exponential curve for backdoor score to ensure clear signals pierce the 0.55 threshold 
        backdoor_risk = self._clip01(backdoor_score * 1.5)

        cluster_quality = data_audit.get("cluster_quality", {})
        if isinstance(cluster_quality, dict):
            separability = self._safe_float(cluster_quality.get("separability_ratio", 0.0))
            sep_risk = self._clip01((1.5 - separability) / 1.5) if separability > 0 else 0.0
        else:
            sep_risk = 0.0

        throughput_check = str(fingerprint.get("throughput_check", "NORMAL"))
        throughput_risk = 1.0 if "SUSPECTED_FAKE" in throughput_check else 0.0

        risk_score = (
            0.80 * backdoor_risk +
            0.15 * sep_risk +
            0.05 * throughput_risk
        )
        return self._clip01(risk_score)

    def update_history(self, content_scores: Dict[str, float],
                       mu_avg: float, sigma_scale: float,
                       cos_root_scores: Optional[Dict[str, float]] = None) -> None:
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
            entry = self._ensure_history_entry(cid)
            hist_prev = entry["ema_score"]

            # 步骤 1: 计算相对竞争势（Z-Score 标准化）
            if sigma_scale > 0:
                z_score = (s_content - mu_avg) / sigma_scale
            else:
                z_score = 0.0

            # 步骤 2: 组合更新信号（相对竞争 + 绝对底线）
            relative_signal = 1.0 / (1.0 + math.exp(-z_score))
            absolute_signal = self._clip01((s_content - self.abs_baseline) / self.abs_span)
            update_signal = (
                self.rel_signal_weight * relative_signal +
                self.abs_signal_weight * absolute_signal
            )

            # 步骤 3: EMA 指数移动平均更新
            hist_new = self.ema_decay * hist_prev + (1.0 - self.ema_decay) * update_signal
            entry["ema_score"] = hist_new
            entry["rounds"] += 1

            # 软隔离：连续低于 soft_prune_threshold 达到 soft_prune_rounds 轮，仅剥夺参与 g_root 的资格
            if hist_new < self.soft_prune_threshold:
                entry["soft_streak"] += 1
            else:
                entry["soft_streak"] = 0
            entry["soft_isolated"] = entry["soft_streak"] >= self.soft_prune_rounds

        # 全局状态持久化落盘
        self._save_state()

    def update_risk_history(
        self,
        report_risks: Dict[str, float],
        cos_root_scores: Optional[Dict[str, float]] = None,
        content_scores: Optional[Dict[str, float]] = None,
        entropies: Optional[Dict[str, float]] = None,
        probe_losses: Optional[Dict[str, float]] = None,
        spectral_scores: Optional[Dict[str, float]] = None,
        pixel_means: Optional[Dict[str, float]] = None,
        pixel_stds: Optional[Dict[str, float]] = None,
        trigger_br_scores: Optional[Dict[str, float]] = None,
        trigger_tl_scores: Optional[Dict[str, float]] = None,
        global_probe_loss: float = 10.0,
        sign_scores: Optional[Dict[str, float]] = None,
        heavy_probe_flags: Optional[Dict[str, bool]] = None,
    ) -> None:
        """
        独立安全流：风险 EMA 更新与风险处置。
        该流不参与 Hist/Raw 的计算，仅在决策层用于隔离、降权、拉黑。
        """
        # --- 方案A: 动态相对阈值 (Dynamic Relative Scaling) ---
        cos_root_median = 0.0
        if cos_root_scores:
            valid_scores = [score for score in cos_root_scores.values() if not math.isnan(score)]
            if valid_scores:
                valid_scores.sort()
                # 使用存活节点的中位数作为本轮的基线锚点，抗受恶意节点攻击性更强
                cos_root_median = valid_scores[len(valid_scores) // 2]
                
        # --- [Scheme G v2] 探针正常受损官方标尺 (Global Probe Baseline) ---
        # 废弃不安全的群体中位数，直接使用从 Server 端提炼的 global_probe_loss
        # -----------------------------------------------------------------
        pixel_mean_median = 0.0
        pixel_mean_mad = 0.0
        if pixel_means:
            mean_vals = [self._safe_float(v) for v in pixel_means.values()]
            if mean_vals:
                pixel_mean_median = float(np.median(mean_vals))
                pixel_mean_mad = float(np.median(np.abs(np.array(mean_vals) - pixel_mean_median)))

        pixel_std_median = 0.0
        pixel_std_mad = 0.0
        if pixel_stds:
            std_vals = [self._safe_float(v) for v in pixel_stds.values()]
            if std_vals:
                pixel_std_median = float(np.median(std_vals))
                pixel_std_mad = float(np.median(np.abs(np.array(std_vals) - pixel_std_median)))

        trigger_br_median = 0.0
        trigger_br_mad = 0.0
        if trigger_br_scores:
            br_vals = [self._safe_float(v) for v in trigger_br_scores.values()]
            if br_vals:
                trigger_br_median = float(np.median(br_vals))
                trigger_br_mad = float(np.median(np.abs(np.array(br_vals) - trigger_br_median)))

        trigger_tl_median = 0.0
        trigger_tl_mad = 0.0
        if trigger_tl_scores:
            tl_vals = [self._safe_float(v) for v in trigger_tl_scores.values()]
            if tl_vals:
                trigger_tl_median = float(np.median(tl_vals))
                trigger_tl_mad = float(np.median(np.abs(np.array(tl_vals) - trigger_tl_median)))

        # Stage-1: 轻量全量筛查，构建群体相对可疑度（不依赖已知触发器模板）
        peer_probe_risk = self._compute_tail_risk(
            probe_losses, tail="high", margin_mad=1.0, scale_mad=2.5, min_mad=0.03
        )
        peer_cos_risk = self._compute_tail_risk(
            cos_root_scores, tail="low", margin_mad=0.8, scale_mad=2.0, min_mad=0.02
        )
        peer_content_risk = self._compute_tail_risk(
            content_scores, tail="low", margin_mad=0.8, scale_mad=2.0, min_mad=0.02
        )
        peer_sign_risk = self._compute_tail_risk(
            sign_scores, tail="low", margin_mad=0.8, scale_mad=2.0, min_mad=0.02
        )

        for cid, report_risk in report_risks.items():
            entry = self._ensure_history_entry(cid)
            risk_prev = float(entry["risk_ema"])
            
            # Access Client Label Entropy
            client_entropy = 1.0
            if entropies is not None:
                client_entropy = self._safe_float(entropies.get(cid, 1.0))

            cos_root = 0.0
            if cos_root_scores is not None:
                cos_root = self._safe_float(cos_root_scores.get(cid, 0.0))
                
            # ==================================================================
            # [Scheme F Phase 5: Dynamic Entropy Shield] (信息熵动态护盾与折跃惩罚)
            # ==================================================================
            # 1. 如果客户端高度偏科 (Low Entropy, e.g. <0.8): 
            #    它是忠诚但能力有限的良民，无论 cos_root 多低都不应该被封杀。
            #    容忍度极高，降维打击被护盾按比例吸收 (grad_risk * client_entropy)。
            # 2. 如果客户端宣称自己是完美全科生 (High Entropy, e.g. >0.90):
            #    既然你拥有完美的 10 个分类，你的梯度方向就必须与 Server 的 g_root_clean 高度重合！
            #    一旦 cos_root 有微小波动，立刻重拳出击。
            
            grad_risk = 0.0
            if client_entropy > 0.90:
                # 全科生审查：仍保持严格，但避免把极小随机漂移放大成持续高风险
                # 由 0.04 放宽到 0.08，降低误判累积速度。
                grad_risk = self._clip01((cos_root_median - cos_root) / 0.08)
            else:
                # 偏科生平滑审查
                # ... (后续无修改)
                if cos_root < 0.10:
                    grad_risk = 1.0 # 就算偏科也不能跟全体反着走
                else:
                    grad_risk = self._clip01((cos_root_median - cos_root) / 0.15)
                # 护盾指数级生效：即使是中度偏科 (entropy~0.75)，其 0.75^3 ≈ 0.42，也能将 1.0 的满分惩罚压制到安全线以下
                grad_risk = grad_risk * (client_entropy ** 3)
                
            # ==================================================================
            # [Scheme S: 梯度符号一致性风险]
            # Label Flip 后门节点因系统性地将梯度推向错误方向，符号一致性持续偷低
            # 正常节点符号一致性 ≈ 0.55继续--0.70；恶意节点理论上低至 0.45 以下
            # ==================================================================
            sign_risk = 0.0
            if sign_scores is not None:
                sign_val = self._safe_float(sign_scores.get(cid, 0.5))
                # 计算全体符号一致性中位数
                all_sign_vals = [v for v in sign_scores.values() if not math.isnan(v)]
                sign_median = sorted(all_sign_vals)[len(all_sign_vals)//2] if all_sign_vals else 0.6
                # 若该节点符号一致性低于中位数 4%，可能是系统性反向推力
                if sign_val < sign_median - 0.04:
                    # 每下降 1% 对应 0.35/0.10 的风险分
                    sign_risk = self._clip01((sign_median - 0.04 - sign_val) / 0.10) * 0.35

            # ==================================================================
            # [Scheme J: 多重混合探针] 动态离群检测风险评估
            # ==================================================================
            probe_risk = 0.0
            probe_entropy = 0.0
            shield_status = "🛡️ SHIELDED" if client_entropy <= 0.95 else "⚔️  EXPOSED"
            if probe_losses is not None:
                probe_entropy = self._safe_float(probe_losses.get(cid, 0.0))
                sampled_this_round = bool(
                    heavy_probe_flags.get(cid, False)
                ) if heavy_probe_flags is not None else probe_entropy > 1e-8

                # 仅在本轮真实做了重探针时，才写入探针历史。
                # 否则会把“未测量=0”误当作真实观测，导致 temporal_risk 虚高。
                if sampled_this_round:
                    if cid not in self._probe_history:
                        self._probe_history[cid] = []
                    self._probe_history[cid].append(probe_entropy)
                    if len(self._probe_history[cid]) > 10:
                        self._probe_history[cid].pop(0)
                
                exposure_scale = 0.0
                if client_entropy > 0.95:
                    exposure_scale = 1.0
                elif client_entropy > 0.90:
                    # 中等加严：0.90~0.95 近似全暴露，避免边界熵节点绕过探针
                    exposure_scale = 0.8 + ((client_entropy - 0.90) / 0.05) * 0.2

                if sampled_this_round and exposure_scale > 0.0 and hasattr(self, '_probe_outlier_threshold'):
                    threshold = self._probe_outlier_threshold
                    if probe_entropy > threshold:
                        base_probe_risk = self._clip01(min(1.0, (probe_entropy - threshold) / 0.18))
                        probe_risk = self._clip01(base_probe_risk * exposure_scale)
                
                # ==================================================================
                # [方案三: ProbeLoss 历史均值持续风险] 
                # 恶意节点 1/2/3 的 ProbeLoss 在 30 轮内始终比正常节点偏高（~1.0~1.5 vs ~0.7~0.9）
                # 以近 10 轮的中位数对比本轮全体中位数，若长期超出 1.25 倍则叠加持续风险分
                # ==================================================================
                if sampled_this_round and len(self._probe_history.get(cid, [])) >= 6:
                    import statistics
                    # 该节点近 10 轮 ProbeLoss 的中位数（含本轮）
                    hist_median = statistics.median(self._probe_history[cid])
                    # 使用 strategy 写入的真实“本轮中位数 + MAD”，避免 threshold/2 的偏置
                    global_probe_median = self._safe_float(
                        getattr(self, "_probe_round_median", 0.0), 0.0
                    )
                    global_probe_mad = self._safe_float(
                        getattr(self, "_probe_round_mad", 0.0), 0.0
                    )
                    baseline = global_probe_median + 0.2 * global_probe_mad
                    if baseline > 0 and hist_median > baseline:
                        # 中等加严：提高持续异常惩罚强度，优先促成封禁
                        hist_scale = max(0.08, baseline * 0.18)
                        hist_risk = self._clip01((hist_median - baseline) / hist_scale) * 0.45
                        if exposure_scale < 1.0:
                            hist_risk *= (0.8 + 0.2 * exposure_scale)
                        probe_risk = self._clip01(probe_risk + hist_risk)
                

            # [Scheme P: 像素统计异常] 利用客户端数据摘要里的像素均值/方差做稳健离群筛查
            # ==================================================================
            pixel_mean_val = self._safe_float(pixel_means.get(cid, 0.0), 0.0) if pixel_means is not None else 0.0
            pixel_std_val = self._safe_float(pixel_stds.get(cid, 0.0), 0.0) if pixel_stds is not None else 0.0
            pixel_risk = 0.0
            if pixel_mean_mad > 1e-6 or pixel_std_mad > 1e-6:
                mean_dev = abs(pixel_mean_val - pixel_mean_median) / max(pixel_mean_mad, 1e-3)
                std_dev = abs(pixel_std_val - pixel_std_median) / max(pixel_std_mad, 1e-3)
                # 超过 2.5 个 MAD 后快速增压风险，抑制触发器型像素污染
                pixel_risk = self._clip01(max((mean_dev - 2.5) / 2.5, (std_dev - 2.5) / 2.5))

            # [Scheme T] 触发器亲和风险：右下角/左上角双触发动态离群
            trigger_br_val = self._safe_float(trigger_br_scores.get(cid, 0.0), 0.0) if trigger_br_scores is not None else 0.0
            trigger_tl_val = self._safe_float(trigger_tl_scores.get(cid, 0.0), 0.0) if trigger_tl_scores is not None else 0.0
            trigger_risk = 0.0
            if trigger_br_scores is not None and trigger_tl_scores is not None:
                br_thr = trigger_br_median + 2.5 * max(trigger_br_mad, 0.02)
                tl_thr = trigger_tl_median + 2.5 * max(trigger_tl_mad, 0.02)
                br_risk = 0.0
                tl_risk = 0.0
                if trigger_br_val > br_thr:
                    br_risk = self._clip01((trigger_br_val - br_thr) / max(0.05, 0.8 * max(trigger_br_mad, 0.02)))
                if trigger_tl_val > tl_thr:
                    tl_risk = self._clip01((trigger_tl_val - tl_thr) / max(0.05, 0.8 * max(trigger_tl_mad, 0.02)))
                trigger_risk = max(br_risk, tl_risk)

            # [Scheme K: 联合破甲] 跨轮方差 (B) 与激活谱比例 (A) 审查
            # ==================================================================
            temporal_risk = 0.0
            spectral_risk = 0.0
            
            # 1. Temporal Risk (B方案)：如果跨轮方差极大，说明它是通过触发器的偶然性逃课的
            temporal_std = 0.0
            if cid in self._probe_history and len(self._probe_history[cid]) >= 5:
                import statistics
                temporal_std = statistics.stdev(self._probe_history[cid])
                # 良民方差通常在 0.1~0.3 之间；高于 0.4 严打 (保守阈值防止误杀)
                if temporal_std > 0.4:
                    temporal_risk = self._clip01((temporal_std - 0.4) / 0.20)
                    
            # 2. Spectral Risk (A方案)：如果特征激活的 top1_ratio 远高于常人
            top1_ratio = 0.0
            if spectral_scores is not None:
                top1_ratio = self._safe_float(spectral_scores.get(cid, 0.0))
                
                if cid not in self._spectral_history:
                    self._spectral_history[cid] = []
                self._spectral_history[cid].append(top1_ratio)
                if len(self._spectral_history[cid]) > 10:
                    self._spectral_history[cid].pop(0)
                
                # ResNet18 avgpool, CIFAR-10, 正常模型的 top1 占比通常不超过 0.12 (12%)
                # 恶意节点 0 (超高 Entropy) 的 top1 可达 0.13+，恶意 1/2/3 与正常节点约 0.09 无法仅靠此区分
                if top1_ratio > 0.15:
                    spectral_risk = self._clip01((top1_ratio - 0.15) / 0.08)

            # [Stage-1 Suspicion] 群体相对可疑分：用于“有怀疑但未定罪”通道
            peer_risk_raw = max(
                self._safe_float(peer_probe_risk.get(cid, 0.0)),
                self._safe_float(peer_cos_risk.get(cid, 0.0)),
                self._safe_float(peer_content_risk.get(cid, 0.0)),
                self._safe_float(peer_sign_risk.get(cid, 0.0)),
            )
            peer_risk_prev = self._safe_float(entry.get("peer_risk_ema", 0.0))
            peer_risk_ema = 0.70 * peer_risk_prev + 0.30 * peer_risk_raw
            entry["last_peer_risk"] = peer_risk_raw
            entry["peer_risk_ema"] = peer_risk_ema
            
            p_msg = f"    🔎 [Client {cid}] H_base={client_entropy:.4f} {shield_status} | "
            p_msg += f"Probe_H={probe_entropy:.4f}(Risk={probe_risk:.2f}) | "
            p_msg += f"T_std={temporal_std:.4f}(Risk={temporal_risk:.2f}) | "
            p_msg += f"S_top1={top1_ratio:.4f}(Risk={spectral_risk:.2f}) | "
            p_msg += f"Pix(mu={pixel_mean_val:.4f},std={pixel_std_val:.4f},Risk={pixel_risk:.2f}) | "
            p_msg += f"Trig(BR={trigger_br_val:.3f},TL={trigger_tl_val:.3f},Risk={trigger_risk:.2f}) | "
            p_msg += f"Sign={sign_risk:.2f} | Peer={peer_risk_ema:.2f}"
            print(p_msg)
                
            # Using Max to ensure independent anomalous signals trigger risk
            channel_risks = (
                report_risk,
                grad_risk,
                probe_risk,
                temporal_risk,
                spectral_risk,
                pixel_risk,
                trigger_risk,
                sign_risk,
                peer_risk_ema,
            )
            instant_risk = self._clip01(max(channel_risks))
            strong_signal_count = sum(
                1 for rv in channel_risks if rv >= self.risk_instant_confirm_threshold
            )
            cross_channel_peak = max(
                report_risk, grad_risk, temporal_risk, spectral_risk, trigger_risk, sign_risk, peer_risk_ema
            )

            # [EMA 贯穿打击] 
            # 如果捕捉到了极其确凿的 1.0 满格死刑（如 信心断层 探出的微型后门），
            # 必须立刻打破 EMA 的动量缓冲，否则在它被缓慢隔离前，后门毒素就会污染全局模型！
            if instant_risk >= 0.99 and strong_signal_count >= self.risk_instant_confirm_channels:
                risk_new = 1.0
            else:
                risk_new = self.risk_ema_decay * risk_prev + (1.0 - self.risk_ema_decay) * instant_risk
                
            entry["risk_ema"] = risk_new
            if probe_risk >= 0.60:
                entry["probe_alert_streak"] += 1
            else:
                entry["probe_alert_streak"] = 0
            if pixel_risk >= 0.60:
                entry["pixel_alert_streak"] += 1
            else:
                entry["pixel_alert_streak"] = 0
            if trigger_risk >= 0.60:
                entry["trigger_alert_streak"] += 1
            else:
                entry["trigger_alert_streak"] = 0
            if peer_risk_ema >= 0.60:
                entry["peer_alert_streak"] += 1
            else:
                entry["peer_alert_streak"] = 0

            if risk_new > self.risk_soft_threshold:
                entry["risk_soft_streak"] += 1
            else:
                entry["risk_soft_streak"] = 0
            entry["risk_isolated"] = entry["risk_soft_streak"] >= self.risk_soft_rounds

            if risk_new > self.risk_hard_threshold:
                entry["risk_hard_streak"] += 1
            else:
                entry["risk_hard_streak"] = 0

            if entry["risk_hard_streak"] >= self.risk_hard_rounds:
                self._mark_blacklist(
                    cid,
                    f"risk_ema_above_{self.risk_hard_threshold:.2f}_for_{self.risk_hard_rounds}_rounds",
                )
            elif (
                cid not in self.blacklist
                and entry["risk_soft_streak"] >= self.risk_soft_blacklist_rounds
                and (
                    entry["risk_hard_streak"] >= 2
                    or (
                        entry["probe_alert_streak"] >= self.risk_soft_blacklist_probe_rounds
                        and cross_channel_peak >= self.risk_soft_blacklist_cross_floor
                    )
                    or (
                        entry["pixel_alert_streak"] >= self.risk_soft_blacklist_pixel_rounds
                        and cross_channel_peak >= self.risk_soft_blacklist_cross_floor
                    )
                    or (
                        entry["trigger_alert_streak"] >= self.risk_soft_blacklist_trigger_rounds
                        and cross_channel_peak >= self.risk_soft_blacklist_cross_floor
                    )
                    or (
                        entry["peer_alert_streak"] >= self.risk_soft_blacklist_peer_rounds
                        and cross_channel_peak >= self.risk_soft_blacklist_cross_floor
                    )
                )
            ):
                # 长期软隔离不再无限旁观，升级为保守硬封禁
                self._mark_blacklist(
                    cid,
                    f"risk_soft_isolation_for_{self.risk_soft_blacklist_rounds}_rounds",
                )

            # [Scheme C - 宽恕正常偏科生，脱钩打分与拦截]
            # 完全去除 Hist/RiskEMA 的软防线导致系统永久封禁的捆绑！
            # 现在，被认为是异类和落后者的客户端 (`any_soft_streak`) 上万轮也不会被封号，
            # 它们只是静静地在后续聚合里被降低权重，保护天然 Non-IID 的合法公民。
            # if entry["risk_isolated"]:
            #     entry["any_soft_streak"] += 1
            # else:
            #     entry["any_soft_streak"] = 0
            # 
            # if cid not in self.blacklist and entry["any_soft_streak"] >= self.soft_blacklist_rounds:
            #     self._mark_blacklist(
            #         cid,
            #         f"soft_isolation_for_{self.soft_blacklist_rounds}_rounds",
            #     )

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
