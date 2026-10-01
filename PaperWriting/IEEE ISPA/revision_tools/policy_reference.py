"""Pure in-memory extraction of the frozen development trust policy.
Generated for the ISPA manuscript, without database connections or credentials.
Decision expressions are retained; persistence methods are removed. This file
is an explanatory artifact, not a new training implementation or new result.
"""
import math
import numpy as np
from typing import Dict, Tuple, Optional

class TrustScoreManager:
    """
    TMAA 信任分管理器
    实现「静态硬门禁 + 动态软感知」的混合信任评估机制，
    并通过正交双流架构分离「历史更新」与「权重计算」。
    """

    def __init__(self, alpha: float=3.0, beta: float=1.0, gamma: float=0.5):
        """
        初始化信任管理器。

        参数:
            alpha: TrustScore 的指数权重（安全因子门控强度，越大则低信任节点惩罚越重）
            beta:  ContentScore 的指数权重（绩效因子强度）
            gamma: HistPerf 的指数权重（历史因子平滑惯性，越小则历史影响越弱）
        """
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.history: Dict[str, dict] = {}
        self.ema_decay = 0.8
        self.lambda_penalty = 5.0
        self._probe_history: Dict[str, list] = {}
        self._spectral_history: Dict[str, list] = {}
        self.tau_tolerance = 0.1
        self.rho_exponent = 2.0
        self.rel_signal_weight = 0.4
        self.abs_signal_weight = 0.6
        self.abs_baseline = 0.4
        self.abs_span = 0.3
        self.soft_prune_threshold = 0.26
        self.soft_prune_rounds = 5
        self.risk_ema_decay = 0.85
        self.risk_report_weight = 0.3
        self.risk_grad_weight = 0.7
        self.risk_soft_threshold = 0.64
        self.risk_soft_rounds = 5
        self.risk_soft_probe_floor = 0.35
        self.risk_soft_trigger_floor = 0.4
        self.risk_soft_pixel_floor = 0.55
        self.risk_soft_grad_floor = 0.2
        self.risk_soft_peer_floor = 0.32
        self.risk_soft_min_hits = 2
        self.risk_soft_relief_margin = 0.04
        self.risk_hard_threshold = 0.9
        self.risk_hard_rounds = 4
        self.risk_hard_min_probe_streak = 2
        self.risk_hard_min_trigger_streak = 1
        self.risk_hard_peer_confirm_floor = 0.7
        self.risk_hard_require_seed_or_trigger = True
        self.risk_raw_attenuation_power = 1.0
        self.risk_instant_confirm_threshold = 0.9
        self.risk_instant_confirm_channels = 2
        self.risk_soft_blacklist_cross_floor = 0.6
        self.risk_soft_blacklist_strong_cross_floor = 0.7
        self.risk_soft_blacklist_probe_rounds = 4
        self.risk_soft_blacklist_pixel_rounds = 3
        self.risk_soft_blacklist_trigger_rounds = 2
        self.risk_soft_blacklist_peer_rounds = 3
        self.c1_fast_track_trigger_floor = 0.62
        self.c1_fast_track_probe_floor = 0.45
        self.c1_fast_track_risk_floor = 0.62
        self.c1_fast_track_rounds = 2
        self.c2_combo_probe_floor = 0.42
        self.c2_combo_peer_floor = 0.24
        self.c2_combo_grad_floor = 0.35
        self.c2_combo_trigger_ceiling = 0.35
        self.c2_combo_pixel_ceiling = 0.65
        self.c2_combo_risk_floor = 0.55
        self.c2_combo_rounds = 5
        self.c2_memory_strong_gain = 2
        self.c2_memory_weak_gain = 1
        self.c2_memory_decay_step = 1
        self.c2_memory_cap = 20
        self.c2_memory_quarantine_score = 8
        self.c2_memory_quarantine_rounds = 2
        self.c2_memory_risk_floor = 0.5
        self.c2_memory_release_score = 3
        self.c2_seed_trigger_floor = 0.52
        self.c2_seed_probe_floor = 0.98
        self.c2_seed_peer_floor = 0.28
        self.c2_seed_grad_floor = 0.2
        self.c2_seed_round_window = 8
        self.peer_gate_margin = 0.12
        self.peer_solo_suppress_threshold = 0.25
        self.soft_blacklist_rounds = 4
        self.risk_soft_blacklist_rounds = 8
        self.blacklist = set()
        self.blacklist_reason: Dict[str, str] = {}

    @staticmethod
    def _clip01(value: float) -> float:
        return max(0.0, min(1.0, value))

    def _ensure_history_entry(self, client_id: str, ema_score: float=0.5, rounds: int=0, risk_ema: float=0.25) -> dict:
        """确保 history 中的节点结构完整（兼容旧版本只含 ema/rounds 的记录）"""
        if client_id not in self.history:
            self.history[client_id] = {'ema_score': float(ema_score), 'rounds': int(rounds), 'soft_streak': 0, 'soft_isolated': False, 'risk_ema': float(risk_ema), 'risk_soft_streak': 0, 'risk_hard_streak': 0, 'risk_isolated': False, 'probe_alert_streak': 0, 'pixel_alert_streak': 0, 'trigger_alert_streak': 0, 'peer_alert_streak': 0, 'peer_risk_ema': 0.0, 'last_peer_risk': 0.0, 'c1_trigger_combo_streak': 0, 'c2_drift_combo_streak': 0, 'c2_probe_streak': 0, 'c2_peer_streak': 0, 'c2_grad_streak': 0, 'c2_memory_score': 0, 'c2_quarantine_streak': 0, 'c2_seeded': False, 'any_soft_streak': 0}
        else:
            entry = self.history[client_id]
            entry.setdefault('ema_score', float(ema_score))
            entry.setdefault('rounds', int(rounds))
            entry.setdefault('soft_streak', 0)
            entry.setdefault('soft_isolated', False)
            entry.setdefault('risk_ema', float(risk_ema))
            entry.setdefault('risk_soft_streak', 0)
            entry.setdefault('risk_hard_streak', 0)
            entry.setdefault('risk_isolated', False)
            entry.setdefault('probe_alert_streak', 0)
            entry.setdefault('pixel_alert_streak', 0)
            entry.setdefault('trigger_alert_streak', 0)
            entry.setdefault('peer_alert_streak', 0)
            entry.setdefault('peer_risk_ema', 0.0)
            entry.setdefault('last_peer_risk', 0.0)
            entry.setdefault('c1_trigger_combo_streak', 0)
            entry.setdefault('c2_drift_combo_streak', 0)
            entry.setdefault('c2_probe_streak', 0)
            entry.setdefault('c2_peer_streak', 0)
            entry.setdefault('c2_grad_streak', 0)
            entry.setdefault('c2_memory_score', 0)
            entry.setdefault('c2_quarantine_streak', 0)
            entry.setdefault('c2_seeded', False)
            entry.setdefault('any_soft_streak', 0)
        return self.history[client_id]

    def _mark_blacklist(self, client_id: str, reason: str) -> None:
        self.blacklist.add(client_id)
        self.blacklist_reason[client_id] = reason
        if client_id in self.history:
            self.history[client_id]['soft_isolated'] = False
            self.history[client_id]['risk_isolated'] = False

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
        metrics = report.get('metrics', {})
        integrity = metrics.get('system_integrity', {})
        m_attest = 0.0 if integrity.get('file_tampered', False) else 1.0
        if m_attest == 0.0:
            return (0.0, 0.0)
        fingerprint = metrics.get('behavior_fingerprint', {})
        throughput_check = fingerprint.get('throughput_check', 'NORMAL')
        a_k = 0.0
        gpu_vol = fingerprint.get('gpu_volatility', 0.0)
        cpu_vol = fingerprint.get('cpu_volatility', 0.0)
        if gpu_vol < 1.0 and cpu_vol < 1.0:
            a_k += 0.4
        if 'SUSPECTED_FAKE' in throughput_check:
            a_k += 0.6
        data_health_audit = metrics.get('data_health_audit', {})
        try:
            backdoor_score = float(data_health_audit.get('backdoor_score', 0.0))
        except (TypeError, ValueError):
            backdoor_score = 0.0
        excess = max(0.0, a_k - self.tau_tolerance)
        penalty = math.exp(-self.lambda_penalty * excess ** self.rho_exponent)
        trust_score = m_attest * penalty
        return (m_attest, trust_score)

    def apply_proxy_loss_penalty(self, client_id: str, clean_loss: float, m_attest: float, trust_score: float) -> Tuple[float, float]:
        """
        基于服务器端的纯净小样本预测结果，对试图隐藏在特征空间内的同构后门进行最后一击。
        任何导致分类边界扭曲的后门行为，不可避免地会在纯净集上表现为暴增的 CrossEntropy Loss。
        """
        SAFE_LOSS_THRESHOLD = 3.5
        if clean_loss > SAFE_LOSS_THRESHOLD:
            self._mark_blacklist(client_id, f'clean_proxy_failure: loss={clean_loss:.4f} > {SAFE_LOSS_THRESHOLD}')
            return (0.0, 0.0)
        loss_penalty = min(1.0, 1.5 / max(clean_loss, 0.1))
        return (m_attest, trust_score * loss_penalty)

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
        return entry['ema_score']

    def is_soft_isolated(self, client_id: str) -> bool:
        if client_id in self.blacklist:
            return False
        entry = self._ensure_history_entry(client_id)
        return bool(entry['soft_isolated'])

    def fetch_risk_ema(self, client_id: str) -> float:
        if client_id in self.blacklist:
            return 1.0
        entry = self._ensure_history_entry(client_id)
        return float(entry['risk_ema'])

    def is_risk_isolated(self, client_id: str) -> bool:
        if client_id in self.blacklist:
            return False
        entry = self._ensure_history_entry(client_id)
        return bool(entry['risk_isolated'])

    def get_blacklist_reason(self, client_id: str) -> str:
        return self.blacklist_reason.get(client_id, 'unknown')

    @staticmethod
    def _safe_float(value, default: float=0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def fetch_risk_detail(self, client_id: str) -> Dict[str, float | int | bool]:
        """返回风险侧关键状态，供策略层可疑池面板读取。"""
        if client_id in self.blacklist:
            return {'risk_ema': 1.0, 'risk_soft_streak': 0, 'risk_hard_streak': self.risk_hard_rounds, 'risk_isolated': False, 'peer_risk_ema': 1.0, 'peer_alert_streak': self.risk_soft_blacklist_peer_rounds, 'last_peer_risk': 1.0, 'c1_trigger_combo_streak': self.c1_fast_track_rounds, 'c2_drift_combo_streak': self.c2_combo_rounds, 'c2_memory_score': self.c2_memory_quarantine_score, 'c2_quarantine_streak': self.c2_memory_quarantine_rounds, 'c2_seeded': True}
        entry = self._ensure_history_entry(client_id)
        return {'risk_ema': float(entry.get('risk_ema', 0.0)), 'risk_soft_streak': int(entry.get('risk_soft_streak', 0)), 'risk_hard_streak': int(entry.get('risk_hard_streak', 0)), 'risk_isolated': bool(entry.get('risk_isolated', False)), 'peer_risk_ema': float(entry.get('peer_risk_ema', 0.0)), 'peer_alert_streak': int(entry.get('peer_alert_streak', 0)), 'last_peer_risk': float(entry.get('last_peer_risk', 0.0)), 'c1_trigger_combo_streak': int(entry.get('c1_trigger_combo_streak', 0)), 'c2_drift_combo_streak': int(entry.get('c2_drift_combo_streak', 0)), 'c2_memory_score': int(entry.get('c2_memory_score', 0)), 'c2_quarantine_streak': int(entry.get('c2_quarantine_streak', 0)), 'c2_seeded': bool(entry.get('c2_seeded', False))}

    def _compute_tail_risk(self, scores: Optional[Dict[str, float]], tail: str='high', margin_mad: float=1.0, scale_mad: float=2.5, min_mad: float=0.001) -> Dict[str, float]:
        """基于 median+MAD 的稳健离群风险，返回 0~1。"""
        if not scores:
            return {}
        vals = [self._safe_float(v) for v in scores.values() if not math.isnan(self._safe_float(v))]
        if len(vals) < 3:
            return {cid: 0.0 for cid in scores}
        med = float(np.median(vals))
        mad = float(np.median(np.abs(np.array(vals) - med)))
        mad = max(mad, min_mad)
        risk_map: Dict[str, float] = {}
        for cid, raw_v in scores.items():
            v = self._safe_float(raw_v)
            if tail == 'high':
                delta = v - (med + margin_mad * mad)
            else:
                delta = med - margin_mad * mad - v
            risk_map[cid] = self._clip01(delta / (scale_mad * mad))
        return risk_map

    def compute_report_risk(self, report: dict) -> float:
        """
        从客户端可信报告中提取当轮风险分 (0~1)。
        仅使用服务端可见字段，不依赖任何本地攻击评估指标。
        """
        metrics = report.get('metrics', {})
        data_audit = metrics.get('data_health_audit', {})
        fingerprint = metrics.get('behavior_fingerprint', {})
        backdoor_score = self._clip01(self._safe_float(data_audit.get('backdoor_score', 0.0)))
        backdoor_risk = self._clip01(backdoor_score * 1.5)
        cluster_quality = data_audit.get('cluster_quality', {})
        if isinstance(cluster_quality, dict):
            separability = self._safe_float(cluster_quality.get('separability_ratio', 0.0))
            sep_risk = self._clip01((1.5 - separability) / 1.5) if separability > 0 else 0.0
        else:
            sep_risk = 0.0
        throughput_check = str(fingerprint.get('throughput_check', 'NORMAL'))
        throughput_risk = 1.0 if 'SUSPECTED_FAKE' in throughput_check else 0.0
        risk_score = 0.8 * backdoor_risk + 0.15 * sep_risk + 0.05 * throughput_risk
        return self._clip01(risk_score)

    def update_history(self, content_scores: Dict[str, float], mu_avg: float, sigma_scale: float, cos_root_scores: Optional[Dict[str, float]]=None) -> None:
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
            hist_prev = entry['ema_score']
            if sigma_scale > 0:
                z_score = (s_content - mu_avg) / sigma_scale
            else:
                z_score = 0.0
            relative_signal = 1.0 / (1.0 + math.exp(-z_score))
            absolute_signal = self._clip01((s_content - self.abs_baseline) / self.abs_span)
            update_signal = self.rel_signal_weight * relative_signal + self.abs_signal_weight * absolute_signal
            hist_new = self.ema_decay * hist_prev + (1.0 - self.ema_decay) * update_signal
            entry['ema_score'] = hist_new
            entry['rounds'] += 1
            if hist_new < self.soft_prune_threshold:
                entry['soft_streak'] += 1
            else:
                entry['soft_streak'] = 0
            entry['soft_isolated'] = entry['soft_streak'] >= self.soft_prune_rounds
        self._save_state()

    def update_risk_history(self, report_risks: Dict[str, float], cos_root_scores: Optional[Dict[str, float]]=None, content_scores: Optional[Dict[str, float]]=None, entropies: Optional[Dict[str, float]]=None, probe_losses: Optional[Dict[str, float]]=None, spectral_scores: Optional[Dict[str, float]]=None, pixel_means: Optional[Dict[str, float]]=None, pixel_stds: Optional[Dict[str, float]]=None, trigger_br_scores: Optional[Dict[str, float]]=None, trigger_tl_scores: Optional[Dict[str, float]]=None, global_probe_loss: float=10.0, sign_scores: Optional[Dict[str, float]]=None, heavy_probe_flags: Optional[Dict[str, bool]]=None) -> None:
        """
        独立安全流：风险 EMA 更新与风险处置。
        该流不参与 Hist/Raw 的计算，仅在决策层用于隔离、降权、拉黑。
        """
        cos_root_median = 0.0
        if cos_root_scores:
            valid_scores = [score for score in cos_root_scores.values() if not math.isnan(score)]
            if valid_scores:
                valid_scores.sort()
                cos_root_median = valid_scores[len(valid_scores) // 2]
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
        peer_probe_risk = self._compute_tail_risk(probe_losses, tail='high', margin_mad=1.0, scale_mad=2.5, min_mad=0.03)
        peer_cos_risk = self._compute_tail_risk(cos_root_scores, tail='low', margin_mad=0.8, scale_mad=2.0, min_mad=0.02)
        peer_content_risk = self._compute_tail_risk(content_scores, tail='low', margin_mad=0.8, scale_mad=2.0, min_mad=0.02)
        peer_sign_risk = self._compute_tail_risk(sign_scores, tail='low', margin_mad=0.8, scale_mad=2.0, min_mad=0.02)
        for cid, report_risk in report_risks.items():
            entry = self._ensure_history_entry(cid)
            risk_prev = float(entry['risk_ema'])
            client_entropy = 1.0
            if entropies is not None:
                client_entropy = self._safe_float(entropies.get(cid, 1.0))
            cos_root = 0.0
            if cos_root_scores is not None:
                cos_root = self._safe_float(cos_root_scores.get(cid, 0.0))
            grad_risk = 0.0
            if client_entropy > 0.9:
                grad_risk = self._clip01((cos_root_median - cos_root) / 0.08)
            else:
                if cos_root < 0.1:
                    grad_risk = 1.0
                else:
                    grad_risk = self._clip01((cos_root_median - cos_root) / 0.15)
                grad_risk = grad_risk * client_entropy ** 3
            sign_risk = 0.0
            if sign_scores is not None:
                sign_val = self._safe_float(sign_scores.get(cid, 0.5))
                all_sign_vals = [v for v in sign_scores.values() if not math.isnan(v)]
                sign_median = sorted(all_sign_vals)[len(all_sign_vals) // 2] if all_sign_vals else 0.6
                if sign_val < sign_median - 0.04:
                    sign_risk = self._clip01((sign_median - 0.04 - sign_val) / 0.1) * 0.35
            probe_risk = 0.0
            probe_entropy = 0.0
            shield_status = '🛡️ SHIELDED' if client_entropy <= 0.95 else '⚔️  EXPOSED'
            if probe_losses is not None:
                probe_entropy = self._safe_float(probe_losses.get(cid, 0.0))
                sampled_this_round = bool(heavy_probe_flags.get(cid, False)) if heavy_probe_flags is not None else probe_entropy > 1e-08
                if sampled_this_round:
                    if cid not in self._probe_history:
                        self._probe_history[cid] = []
                    self._probe_history[cid].append(probe_entropy)
                    if len(self._probe_history[cid]) > 10:
                        self._probe_history[cid].pop(0)
                exposure_scale = 0.0
                if client_entropy > 0.95:
                    exposure_scale = 1.0
                elif client_entropy > 0.9:
                    exposure_scale = 0.8 + (client_entropy - 0.9) / 0.05 * 0.2
                if sampled_this_round and exposure_scale > 0.0 and hasattr(self, '_probe_outlier_threshold'):
                    threshold = self._probe_outlier_threshold
                    if probe_entropy > threshold:
                        base_probe_risk = self._clip01(min(1.0, (probe_entropy - threshold) / 0.18))
                        probe_risk = self._clip01(base_probe_risk * exposure_scale)
                if sampled_this_round and len(self._probe_history.get(cid, [])) >= 6:
                    import statistics
                    hist_median = statistics.median(self._probe_history[cid])
                    global_probe_median = self._safe_float(getattr(self, '_probe_round_median', 0.0), 0.0)
                    global_probe_mad = self._safe_float(getattr(self, '_probe_round_mad', 0.0), 0.0)
                    baseline = global_probe_median + 0.2 * global_probe_mad
                    if baseline > 0 and hist_median > baseline:
                        hist_scale = max(0.08, baseline * 0.18)
                        hist_risk = self._clip01((hist_median - baseline) / hist_scale) * 0.45
                        if exposure_scale < 1.0:
                            hist_risk *= 0.8 + 0.2 * exposure_scale
                        probe_risk = self._clip01(probe_risk + hist_risk)
            pixel_mean_val = self._safe_float(pixel_means.get(cid, 0.0), 0.0) if pixel_means is not None else 0.0
            pixel_std_val = self._safe_float(pixel_stds.get(cid, 0.0), 0.0) if pixel_stds is not None else 0.0
            pixel_risk = 0.0
            if pixel_mean_mad > 1e-06 or pixel_std_mad > 1e-06:
                mean_dev = abs(pixel_mean_val - pixel_mean_median) / max(pixel_mean_mad, 0.001)
                std_dev = abs(pixel_std_val - pixel_std_median) / max(pixel_std_mad, 0.001)
                pixel_risk = self._clip01(max((mean_dev - 2.5) / 2.5, (std_dev - 2.5) / 2.5))
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
            temporal_risk = 0.0
            spectral_risk = 0.0
            temporal_std = 0.0
            if cid in self._probe_history and len(self._probe_history[cid]) >= 5:
                import statistics
                temporal_std = statistics.stdev(self._probe_history[cid])
                if temporal_std > 0.4:
                    temporal_risk = self._clip01((temporal_std - 0.4) / 0.2)
            top1_ratio = 0.0
            if spectral_scores is not None:
                top1_ratio = self._safe_float(spectral_scores.get(cid, 0.0))
                if cid not in self._spectral_history:
                    self._spectral_history[cid] = []
                self._spectral_history[cid].append(top1_ratio)
                if len(self._spectral_history[cid]) > 10:
                    self._spectral_history[cid].pop(0)
                if top1_ratio > 0.15:
                    spectral_risk = self._clip01((top1_ratio - 0.15) / 0.08)
            peer_risk_raw = max(self._safe_float(peer_probe_risk.get(cid, 0.0)), self._safe_float(peer_cos_risk.get(cid, 0.0)), self._safe_float(peer_content_risk.get(cid, 0.0)), self._safe_float(peer_sign_risk.get(cid, 0.0)))
            peer_risk_prev = self._safe_float(entry.get('peer_risk_ema', 0.0))
            peer_risk_ema = 0.7 * peer_risk_prev + 0.3 * peer_risk_raw
            entry['last_peer_risk'] = peer_risk_raw
            entry['peer_risk_ema'] = peer_risk_ema
            primary_non_peer = max(report_risk, grad_risk, probe_risk, temporal_risk, spectral_risk, pixel_risk, trigger_risk, sign_risk)
            peer_effective = min(peer_risk_ema, primary_non_peer + self.peer_gate_margin)
            if primary_non_peer < self.peer_solo_suppress_threshold:
                peer_effective *= 0.6
            peer_effective = self._clip01(peer_effective)
            p_msg = f'    🔎 [Client {cid}] H_base={client_entropy:.4f} {shield_status} | '
            p_msg += f'Probe_H={probe_entropy:.4f}(Risk={probe_risk:.2f}) | '
            p_msg += f'T_std={temporal_std:.4f}(Risk={temporal_risk:.2f}) | '
            p_msg += f'S_top1={top1_ratio:.4f}(Risk={spectral_risk:.2f}) | '
            p_msg += f'Pix(mu={pixel_mean_val:.4f},std={pixel_std_val:.4f},Risk={pixel_risk:.2f}) | '
            p_msg += f'Trig(BR={trigger_br_val:.3f},TL={trigger_tl_val:.3f},Risk={trigger_risk:.2f}) | '
            p_msg += f'Sign={sign_risk:.2f} | Peer={peer_risk_ema:.2f}->{peer_effective:.2f}'
            print(p_msg)
            channel_risks = (report_risk, grad_risk, probe_risk, temporal_risk, spectral_risk, pixel_risk, trigger_risk, sign_risk, peer_effective)
            instant_risk = self._clip01(max(channel_risks))
            strong_signal_count = sum((1 for rv in channel_risks if rv >= self.risk_instant_confirm_threshold))
            cross_channel_peak = max(report_risk, grad_risk, temporal_risk, spectral_risk, trigger_risk, sign_risk, peer_effective)
            instant_kill_switch = instant_risk >= 0.99 and strong_signal_count >= self.risk_instant_confirm_channels and (trigger_risk >= self.c2_seed_trigger_floor or probe_risk >= self.c2_seed_probe_floor)
            if instant_kill_switch:
                risk_new = 1.0
            else:
                risk_new = self.risk_ema_decay * risk_prev + (1.0 - self.risk_ema_decay) * instant_risk
            entry['risk_ema'] = risk_new
            if probe_risk >= 0.6:
                entry['probe_alert_streak'] += 1
            else:
                entry['probe_alert_streak'] = 0
            if pixel_risk >= 0.6:
                entry['pixel_alert_streak'] += 1
            else:
                entry['pixel_alert_streak'] = 0
            if trigger_risk >= 0.6:
                entry['trigger_alert_streak'] += 1
            else:
                entry['trigger_alert_streak'] = 0
            if peer_risk_ema >= 0.6:
                entry['peer_alert_streak'] += 1
            else:
                entry['peer_alert_streak'] = 0
            if not entry.get('c2_seeded', False):
                early_round = int(entry.get('rounds', 0)) <= self.c2_seed_round_window
                seed_by_trigger = trigger_risk >= self.c2_seed_trigger_floor
                seed_by_extreme_drift = probe_risk >= self.c2_seed_probe_floor and peer_effective >= self.c2_seed_peer_floor and (grad_risk >= self.c2_seed_grad_floor)
                if early_round and (seed_by_trigger or seed_by_extreme_drift):
                    entry['c2_seeded'] = True
                    print(f'    🧬 [Client {cid}] C2 Seed Armed | trig={trigger_risk:.2f} | probe={probe_risk:.2f} | peer={peer_effective:.2f} | grad={grad_risk:.2f}')
            c1_hit = client_entropy > 0.95 and trigger_risk >= self.c1_fast_track_trigger_floor and (probe_risk >= self.c1_fast_track_probe_floor or entry['probe_alert_streak'] >= 2) and (risk_new >= self.c1_fast_track_risk_floor)
            if c1_hit:
                entry['c1_trigger_combo_streak'] += 1
            else:
                entry['c1_trigger_combo_streak'] = 0
            c2_enabled = bool(entry.get('c2_seeded', False))
            peer_signal = max(peer_effective, peer_risk_raw)
            c2_probe_hit = c2_enabled and client_entropy > 0.95 and (probe_risk >= self.c2_combo_probe_floor)
            c2_peer_hit = c2_enabled and client_entropy > 0.95 and (peer_signal >= self.c2_combo_peer_floor)
            c2_grad_hit = c2_enabled and client_entropy > 0.95 and (grad_risk >= self.c2_combo_grad_floor or sign_risk >= 0.15)
            if c2_probe_hit:
                entry['c2_probe_streak'] += 1
            else:
                entry['c2_probe_streak'] = max(0, entry['c2_probe_streak'] - 1)
            if c2_peer_hit:
                entry['c2_peer_streak'] += 1
            else:
                entry['c2_peer_streak'] = max(0, entry['c2_peer_streak'] - 1)
            if c2_grad_hit:
                entry['c2_grad_streak'] += 1
            else:
                entry['c2_grad_streak'] = max(0, entry['c2_grad_streak'] - 1)
            c2_hit_count = int(c2_probe_hit) + int(c2_peer_hit) + int(c2_grad_hit)
            if c2_hit_count >= 2 and trigger_risk <= self.c2_combo_trigger_ceiling and (pixel_risk <= self.c2_combo_pixel_ceiling) and (risk_new >= self.c2_combo_risk_floor - 0.06):
                entry['c2_drift_combo_streak'] += 1
            else:
                entry['c2_drift_combo_streak'] = max(0, entry['c2_drift_combo_streak'] - 1)
            c2_memory_score_prev = int(entry.get('c2_memory_score', 0))
            c2_mild_signal = c2_enabled and client_entropy > 0.95 and (probe_risk >= max(0.28, self.c2_combo_probe_floor - 0.1) or peer_signal >= max(0.18, self.c2_combo_peer_floor - 0.06) or grad_risk >= max(0.22, self.c2_combo_grad_floor - 0.13) or (sign_risk >= 0.12))
            if c2_enabled and c2_hit_count >= 2 and (risk_new >= self.c2_combo_risk_floor - 0.08):
                c2_memory_score = c2_memory_score_prev + self.c2_memory_strong_gain
            elif c2_mild_signal and risk_new >= self.c2_memory_risk_floor - 0.05:
                c2_memory_score = c2_memory_score_prev + self.c2_memory_weak_gain
            else:
                c2_memory_score = c2_memory_score_prev - self.c2_memory_decay_step
            c2_memory_score = max(0, min(self.c2_memory_cap, c2_memory_score))
            entry['c2_memory_score'] = c2_memory_score
            c2_quarantine_hit = c2_enabled and c2_memory_score >= self.c2_memory_quarantine_score and (risk_new >= self.c2_memory_risk_floor) and (trigger_risk <= self.c2_combo_trigger_ceiling) and (pixel_risk <= self.c2_combo_pixel_ceiling + 0.1)
            if c2_quarantine_hit:
                entry['c2_quarantine_streak'] += 1
            else:
                q_decay = 2 if c2_memory_score <= self.c2_memory_release_score and risk_new < self.c2_memory_risk_floor - 0.08 else 1
                entry['c2_quarantine_streak'] = max(0, entry['c2_quarantine_streak'] - q_decay)
            c2_quarantine_active = entry['c2_quarantine_streak'] >= self.c2_memory_quarantine_rounds
            if c2_enabled and (c2_memory_score >= self.c2_memory_quarantine_score - 1 or c2_quarantine_active):
                print(f"    🧬 [Client {cid}] C2 Memory | score={c2_memory_score:02d} | QStreak={entry['c2_quarantine_streak']} | hit={c2_hit_count} | risk={risk_new:.3f} | trig={trigger_risk:.2f} | pix={pixel_risk:.2f}")
            soft_hit_count = int(probe_risk >= self.risk_soft_probe_floor) + int(trigger_risk >= self.risk_soft_trigger_floor) + int(pixel_risk >= self.risk_soft_pixel_floor) + int(grad_risk >= self.risk_soft_grad_floor) + int(sign_risk >= 0.12) + int(peer_effective >= self.risk_soft_peer_floor)
            soft_strong = bool(entry.get('c2_seeded', False)) or trigger_risk >= self.risk_soft_trigger_floor or pixel_risk >= self.risk_soft_pixel_floor
            soft_gate = soft_strong or soft_hit_count >= self.risk_soft_min_hits
            if risk_new > self.risk_soft_threshold and soft_gate:
                entry['risk_soft_streak'] += 1
            else:
                decay_step = 2 if risk_new < self.risk_soft_threshold - self.risk_soft_relief_margin and soft_hit_count == 0 and (not soft_strong) else 1
                entry['risk_soft_streak'] = max(0, entry['risk_soft_streak'] - decay_step)
            entry['risk_isolated'] = entry['risk_soft_streak'] >= self.risk_soft_rounds or c2_quarantine_active
            hard_evidence = entry['probe_alert_streak'] >= self.risk_hard_min_probe_streak or entry['trigger_alert_streak'] >= self.risk_hard_min_trigger_streak or (peer_effective >= self.risk_hard_peer_confirm_floor and (grad_risk >= 0.25 or sign_risk >= 0.15))
            hard_gate = not self.risk_hard_require_seed_or_trigger or bool(entry.get('c2_seeded', False)) or entry['trigger_alert_streak'] >= self.risk_hard_min_trigger_streak
            if risk_new > self.risk_hard_threshold and hard_evidence and hard_gate:
                entry['risk_hard_streak'] += 1
            else:
                entry['risk_hard_streak'] = max(0, entry['risk_hard_streak'] - 1)
            if entry['risk_hard_streak'] >= self.risk_hard_rounds:
                self._mark_blacklist(cid, f'risk_ema_above_{self.risk_hard_threshold:.2f}_for_{self.risk_hard_rounds}_rounds')
            elif cid not in self.blacklist and entry['c1_trigger_combo_streak'] >= self.c1_fast_track_rounds:
                self._mark_blacklist(cid, f'c1_trigger_combo_for_{self.c1_fast_track_rounds}_rounds')
            elif cid not in self.blacklist and entry['c2_drift_combo_streak'] >= self.c2_combo_rounds and (entry['c2_probe_streak'] >= max(3, self.c2_combo_rounds - 2)) and (entry['c2_peer_streak'] >= max(2, self.c2_combo_rounds - 3) or entry['c2_grad_streak'] >= max(2, self.c2_combo_rounds - 3)) and (risk_new >= self.c2_combo_risk_floor):
                self._mark_blacklist(cid, f'c2_drift_combo_for_{self.c2_combo_rounds}_rounds')
            elif cid not in self.blacklist and entry['risk_soft_streak'] >= self.risk_soft_blacklist_rounds and (risk_new >= self.risk_soft_threshold):
                seeded = bool(entry.get('c2_seeded', False))
                has_strong_visual = entry['trigger_alert_streak'] >= self.risk_soft_blacklist_trigger_rounds or entry['pixel_alert_streak'] >= self.risk_soft_blacklist_pixel_rounds
                has_seeded_drift = seeded and (entry['probe_alert_streak'] >= self.risk_soft_blacklist_probe_rounds or entry['peer_alert_streak'] >= self.risk_soft_blacklist_peer_rounds or entry['c2_drift_combo_streak'] >= max(3, self.c2_combo_rounds - 1))
                strong_cross = cross_channel_peak >= self.risk_soft_blacklist_strong_cross_floor
                promote_soft_blacklist = entry['risk_hard_streak'] >= 2 or (has_strong_visual and strong_cross) or (has_seeded_drift and cross_channel_peak >= self.risk_soft_blacklist_cross_floor)
                if promote_soft_blacklist:
                    self._mark_blacklist(cid, f'risk_soft_isolation_for_{self.risk_soft_blacklist_rounds}_rounds')
        self._save_state()

    def calculate_raw_score(self, client_id: str, trust_score: float, content_score: float) -> float:
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
        raw_score = trust_score ** self.alpha * content_score ** self.beta * hist_perf ** self.gamma
        return raw_score

    def _save_state(self):
        pass
