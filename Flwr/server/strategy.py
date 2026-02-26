import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Subset
import torchvision
import torchvision.transforms as transforms
from collections import deque

from audit import AuditLogger

# 为导入 Client 模块添加路径 (如果需要)
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Client'))
try:
    from model import get_resnet18
except ImportError:
    # 回退方案: 如果路径不匹配，手动定义或模拟
    def get_resnet18(num_classes=10):
        import torchvision.models as models
        net = models.resnet18(weights=None)
        net.conv1 = nn.Conv2d(3, 64, kernel_size=3, stride=1, padding=1, bias=False)
        net.maxpool = nn.Identity()
        net.fc = nn.Linear(net.fc.in_features, num_classes)
        return net

# ==================== TMAA 信任评估引擎 (TrustScore Engine) ====================
class TrustScoreManager:
    """
    TMAA 信任分管理模块
    实现公式: TrustScore_k = M_attest * (α*DataQual + β*BehavScore + γ*HistPerf)
    """
    def __init__(self, alpha=0.4, beta=0.4, gamma=0.2):
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.history = {}  # client_id -> { "ema_score": float, "rounds": int }
        self.ema_decay = 0.8  # 历史分数的衰减系数

    def calculate_trust_score(self, client_id: str, report: Dict[str, Any], l4_metrics: Dict[str, Any]) -> Tuple[float, Dict[str, float]]:
        """
        计算综合信任分 (0.0 - 1.0)
        """
        metrics = report.get("metrics", {})
        
        # --- Part A: 静态硬门禁 (M_attest) ---
        integrity = metrics.get("system_integrity", {})
        m_attest = 0.0 if integrity.get("file_tampered", False) else 1.0
        
        if m_attest == 0:
            return 0.0, {"m_attest": 0.0, "data_qual": 0.0, "behav_score": 0.0, "hist_perf": 0.0}

        # --- Part B: 数据质量评分 (DataQual) ---
        # 综合考虑 Initial Loss 偏差和聚类质量
        data_audit = metrics.get("data_health_audit", {})
        loss_dev = l4_metrics.get("loss_deviation", 0.0)
        # 用指数衰减函数将 deviation 映射到 0-1
        # deviation=0 -> 1.0, deviation=3 -> ~0.05
        s_loss = np.exp(-loss_dev / 1.5) 
        
        cluster_q = data_audit.get("cluster_quality", {})
        s_cluster = cluster_q.get("separability_ratio", 0.5) if isinstance(cluster_q, dict) else 0.5
        
        data_qual = 0.7 * s_loss + 0.3 * s_cluster
        
        # --- Part C: 训练行为评分 (BehavScore) ---
        # 综合考虑 波动率、余弦相似度、范数一致性
        fingerprint = metrics.get("behavior_fingerprint", {})
        
        # 1. 波动度检查 (S_vol)
        gpu_vol = fingerprint.get("gpu_volatility", 0.0)
        cpu_vol = fingerprint.get("cpu_volatility", 0.0)
        s_vol = 1.0 if (gpu_vol > 0.01 or cpu_vol > 0.05) else 0.2
        
        # 2. 方向一致性 (S_dir)
        cosine_sim = l4_metrics.get("cosine_sim", 1.0)
        # 将 -1~1 映射到 0~1，且负相关惩罚加重
        s_dir = max(0, (cosine_sim + 1) / 2) if cosine_sim > 0 else (cosine_sim + 1) * 0.5
        
        # 3. 范数合理性 (S_norm)
        norm_ratio = l4_metrics.get("norm_ratio", 1.0)
        # ratio=1 -> 1.0, ratio=10 -> 0.0
        s_norm = max(0, 1.0 - abs(norm_ratio - 1.0) / 5.0)
        
        behav_score = 0.3 * s_vol + 0.4 * s_dir + 0.3 * s_norm
        
        # --- Part D: 历史表现评分 (HistPerf) ---
        if client_id not in self.history:
            hist_perf = 0.5  # 初始中立信誉
        else:
            hist_perf = self.history[client_id]["ema_score"]

        # --- Final TrustScore ---
        raw_score = self.alpha * data_qual + self.beta * behav_score + self.gamma * hist_perf
        final_score = m_attest * raw_score
        
        # 更新历史 (EMA)
        if client_id not in self.history:
            self.history[client_id] = {"ema_score": final_score, "rounds": 1}
        else:
            old_ema = self.history[client_id]["ema_score"]
            self.history[client_id]["ema_score"] = self.ema_decay * old_ema + (1 - self.ema_decay) * final_score
            self.history[client_id]["rounds"] += 1
            
        return final_score, {
            "m_attest": m_attest,
            "data_qual": data_qual,
            "behav_score": behav_score,
            "hist_perf": hist_perf
        }

# ==================== TMAA 优先贡献度验证 (Prioritized Contribution Validation) ====================
class ContributionValidator:
    """
    TMAA 效果属性审查模块
    基于 Root Dataset 的梯度一致性检测
    """
    def __init__(self, root_sample_size: int = 200, window_size: int = 5):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = get_resnet18(num_classes=10).to(self.device).eval()
        self.root_loader = self._prepare_root_dataset(root_sample_size)
        
        # 自适应阈值状态
        self.sim_history = deque(maxlen=window_size)
        self.mu_sim = 0.1  # 初始基准相似度阈值
        self.sigma_sim = 0.05

    def _prepare_root_dataset(self, size: int):
        """准备服务器端可信根数据集"""
        transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010))
        ])
        try:
            # 优先加载真实数据 (服务器端通常有固定存储)
            full_testset = torchvision.datasets.CIFAR10(root='./data', train=False, download=True, transform=transform)
            indices = np.random.choice(len(full_testset), size, replace=False)
            root_subset = Subset(full_testset, indices)
        except:
            # 合成数据保障环境可用
            from torchvision.datasets import FakeData
            root_subset = FakeData(size=size, image_size=(3, 32, 32), num_classes=10, transform=transform)
            
        return DataLoader(root_subset, batch_size=size, shuffle=False)

    def compute_reference_gradient(self, global_params: Parameters) -> np.ndarray:
        """基于根数据集计算黄金标准梯度 (g_root)"""
        # 1. 加载全局参数到模型
        ndarrays = fl.common.parameters_to_ndarrays(global_params)
        params_dict = zip(self.model.state_dict().keys(), ndarrays)
        state_dict = {k: torch.tensor(v) for k, v in params_dict}
        self.model.load_state_dict(state_dict, strict=True)
        
        # 2. 计算梯度
        self.model.zero_grad()
        criterion = nn.CrossEntropyLoss()
        
        data, target = next(iter(self.root_loader))
        data, target = data.to(self.device), target.to(self.device)
        
        output = self.model(data)
        loss = criterion(output, target)
        loss.backward()
        
        # 3. 提取扁平化梯度向量
        grads = []
        for param in self.model.parameters():
            if param.grad is not None:
                grads.append(param.grad.view(-1).cpu().numpy())
        
        return np.concatenate(grads)

    def validate_contribution(self, g_k: np.ndarray, g_root: np.ndarray) -> Tuple[float, float]:
        """一致性检测与自适应评分"""
        # 余弦相似度计算
        dot_prod = np.dot(g_k, g_root)
        norm_k = np.linalg.norm(g_k) + 1e-9
        norm_root = np.linalg.norm(g_root) + 1e-9
        cos_sim = dot_prod / (norm_k * norm_root)
        
        # 动态阈值逻辑 (k=1)
        # Threshold_dynamic = max(0, mu_sim - sigma_sim)
        threshold = max(0.0, self.mu_sim - 1.0 * self.sigma_sim)
        
        # ReLU 激活并限制在 0-1
        score = max(0.0, cos_sim - threshold)
        # 归一化 (可选，这里防止相似度极低但仍通过的情况)
        if cos_sim < 0: score = 0.0 
        
        return score, cos_sim

    def update_threshold_stats(self, positive_sims: List[float]):
        """更新历史共识统计信息"""
        if not positive_sims: return
        
        self.sim_history.append(np.mean(positive_sims))
        if len(self.sim_history) > 1:
            self.mu_sim = np.mean(self.sim_history)
            self.sigma_sim = np.std(self.sim_history) + 1e-5

# ==================== TMAA 策略匹配器 (Policy Engine) ====================


# ==================== TMAA 安全聚合策略 ====================
class TMAA_FedAvg(fl.server.strategy.FedAvg):
    """
    TMAA 增强版 FedAvg 策略
    
    功能:
        在聚合参数前，拦截并验证客户端提交的 '可信报告' (Trust Report)。
        根据硬件指纹和签名验证结果，决定是否接受该客户端的更新。
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.policy_engine = PolicyMatcher()
        self.trust_manager = TrustScoreManager()
        self.contribution_validator = ContributionValidator()  # 初始化贡献度验证器
        self.audit_logger = AuditLogger()

    def aggregate_fit(
        self,
        server_round: int,
        results: List[Tuple[ClientProxy, FitRes]],
        failures: List[str | BaseException],
    ) -> Tuple[Optional[Parameters], Dict[str, Scalar]]:
        
        self.audit_logger.log(f"\n🛡️  [TMAA Server] Round {server_round} | 接收客户端数据 (Passive Mode)...")
        
        # [步骤 1] 预扫描: 收集所有可信报告和模型更新用于跨客户端分析
        client_reports = {} # 客户端ID -> 报告
        initial_losses = []
        
        # L4 符号翻转检测: 收集扁平化更新
        all_updates = [] # List[np.ndarray]
        client_update_map = {} # 客户端ID -> np.ndarray
        
        import numpy as np
        
        for client, fit_res in results:
            # 1. 收集报告
            if "trust_report_json" in fit_res.metrics:
                try:
                    payload = json.loads(fit_res.metrics["trust_report_json"])
                    report = payload.get("trust_report", payload)
                    client_reports[client.cid] = report
                    
                    # 收集初始损失用于 L4 分析
                    data_audit = report["metrics"].get("data_health_audit", {})
                    init_loss = data_audit.get("initial_loss", None)
                    if init_loss is not None:
                        initial_losses.append(init_loss)
                        
                except:
                    pass
            
            # 2. 收集模型参数（扁平化）
            # fit_res.parameters 是 Parameters(tensors=[bytes])，需要反序列化
            try:
                # 反序列化为 List[np.ndarray]
                weights = fl.common.parameters_to_ndarrays(fit_res.parameters)
                # 将所有层扁平化为单个向量
                flat_update = np.concatenate([w.flatten() for w in weights])
                all_updates.append(flat_update)
                client_update_map[client.cid] = flat_update
            except Exception as e:
                self.audit_logger.log(f"    ⚠️ [客户端 {client.cid}] 参数反序列化失败: {e}")

        # 计算 L4 策略的全局统计信息
        median_loss = np.median(initial_losses) if initial_losses else 0.0
        mad_loss = np.median(np.abs(np.array(initial_losses) - median_loss)) if initial_losses else 0.0
        mad_loss = max(mad_loss, 1e-6)
        
        # [L4] 缩放攻击: 计算中位数范数
        all_norms = [np.linalg.norm(u) for u in all_updates]
        median_norm = np.median(all_norms) if all_norms else 1.0
        norm_threshold = median_norm * 2.0
        if median_norm < 1e-4: norm_threshold = 1.0 # 如果所有客户端都接近 0 偏差，避免裁剪
        
        # 计算平均更新向量（伪梯度方向）
        avg_update_vector = None
        global_grad_norm = 0.0
        if all_updates:
            # 所有更新的均值（参考方向）
            avg_update_vector = np.mean(all_updates, axis=0)
            global_grad_norm = np.linalg.norm(avg_update_vector) + 1e-9
        
        self.audit_logger.log(f"    📊 [L4 Analysis] Global InitLoss: Med={median_loss:.4f} | Global Norm: Med={median_norm:.2f} (Clip > {norm_threshold:.2f})")

        # [步骤 3] 优先贡献度准备: 计算聚合基准 (Root Gradient)
        self.audit_logger.log(f"🔍 [Round {server_round}] 计算验证基准 (Root Gradient)...")
        # 获取当前模型参数的 Parameters 对象
        # 如果是第一轮，使用 strategy 初始化的参数
        current_params = results[0][1].parameters if results else Parameters(tensors=[], tensor_type='')
        g_root = self.contribution_validator.compute_reference_gradient(current_params)

        valid_results = []
        rejected_count = 0
        round_positive_sims = [] # 用于更新自适应阈值
        
        # [步骤 2] 主循环: 验证和记录日志
        for client, fit_res in results:
            metrics = fit_res.metrics
            client_logs = []  # [原子性] 缓冲此客户端的日志

            if client.cid in client_reports:
                try:
                    report = client_reports[client.cid]
                    tee_id = report['header']['device_id']
                    
                    # 策略检查
                    is_compliant, reason = self.policy_engine.check_compliance(report)
                    
                    l4_status = ""
                    
                    # [L4 检查 1] 初始损失一致性
                    data_audit = report["metrics"].get("data_health_audit", {})
                    # 修复: 处理 JSON 中 initial_loss 为 null 的情况
                    my_init_loss = data_audit.get("initial_loss")
                    if my_init_loss is None: my_init_loss = 0.0
                    
                    loss_deviation = abs(my_init_loss - median_loss) / (mad_loss + 1e-9)
                    
                    if loss_deviation > 3.0: 
                        l4_status += f" ⚠️ 初始损失异常值 (+{loss_deviation:.1f}σ)"
                    
                    # [L4 检查 2] 逐层范数过滤
                    client_meta = report["metrics"].get("client_reported_meta", {})
                    layer_updates = client_meta.get("layer_updates", [])
                    # 修复: 过滤列表中的 None 值
                    if layer_updates:
                        layer_updates = [x for x in layer_updates if x is not None]

                    if layer_updates and len(layer_updates) > 2:
                        extractor_norm = np.mean(layer_updates[:-2]) + 1e-9
                        classifier_norm = layer_updates[-1]
                        impact_ratio = classifier_norm / extractor_norm
                        if impact_ratio > 10.0:
                             l4_status += f" ⚠️ 头部过重 (比例 {impact_ratio:.1f})"

                    # [L4 检查 3] 余弦相似度（符号翻转）
                    my_update = client_update_map.get(client.cid)
                    cosine_sim = 1.0
                    norm_ratio = 1.0
                    
                    if my_update is not None and avg_update_vector is not None:
                        my_norm = np.linalg.norm(my_update) + 1e-9
                        dot_prod = np.dot(my_update, avg_update_vector)
                        cosine_sim = dot_prod / (my_norm * global_grad_norm)
                        norm_ratio = my_norm / median_norm

                        if cosine_sim < -0.5:
                            l4_status += f" ⚠️ 符号翻转警告 (Cos={cosine_sim:.2f})"

                        if my_norm < 1e-4:
                             l4_status += f" ❌ 零梯度（懒惰）"
                        
                        if my_norm > norm_threshold:
                            l4_status += f" ⚠️ 缩放攻击检测 (范数 {my_norm:.1f} > 阈值 {norm_threshold:.1f})"
                    
                    # --- 核心: 计算 TrustScore_k ---
                    l4_metrics = {
                        "loss_deviation": loss_deviation,
                        "cosine_sim": cosine_sim,
                        "norm_ratio": norm_ratio
                    }
                    trust_score, breakdown = self.trust_manager.calculate_trust_score(client.cid, report, l4_metrics)
                    
                    # --- 阶段 4: 优先贡献度验证 (g_root 校验) ---
                    # 计算此客户端的梯度向量 (差分)
                    g_k = my_update if my_update is not None else np.zeros_like(g_root)
                    
                    # 验证贡献度
                    contrib_score, cos_sim = self.contribution_validator.validate_contribution(g_k, g_root)
                    
                    # 汇总相似度用于后续更新阈值
                    if cos_sim > 0: round_positive_sims.append(cos_sim)
                    
                    # 记录审查结果
                    report["trust_score"] = trust_score
                    report["contribution_score"] = round(float(contrib_score), 3)
                    report["cosine_similarity"] = round(float(cos_sim), 3)
                    
                    # 最终判定逻辑: 综合信誉分与贡献度
                    # 规则: 如果贡献度为 0 (反向更新)，即刻拒绝
                    is_compliant = (trust_score >= 0.5) and (contrib_score > 0)
                    
                    reason = "✅ 合规" if is_compliant else \
                             (f"❌ 贡献无效 (Sim={cos_sim:.2f})" if contrib_score <= 0 else f"❌ 信任分数过低 ({trust_score:.2f})")
                    
                    status_icon = "✅" if is_compliant else "❌"
                    client_logs.append(f"    🛡️  [T-Score] {trust_score:.2f} | [C-Score] {contrib_score:.2f} (Sim={cos_sim:.2f})")
                    client_logs.append(f"    📄 [Client {client.cid}] TEE: {tee_id[:8]}.. | {status_icon} Policy: {reason}{l4_status}")

                    # [新功能] 记录数据统计特征（数据指纹记录）
                    cluster_q = data_audit.get("cluster_quality")
                    if isinstance(cluster_q, dict):
                         q_str = f"可分性={cluster_q.get('separability_ratio', '?')}"
                    else:
                         q_str = "N/A"

                    client_logs.append(f"       📊 数据审计: 聚类={q_str} | 初始损失={my_init_loss:.3f}")
                    
                    # 记录资源摘要 (v2.0 新增)
                    resource_sum = report["metrics"].get("resource_summary", {})
                    if resource_sum:
                        client_logs.append(
                            f"       🖥️  资源使用: CPU={resource_sum.get('avg_cpu', '?')}% "
                            f"GPU={resource_sum.get('avg_gpu', '?')}% "
                            f"内存={resource_sum.get('avg_memory_mb', '?')}MB "
                            f"({resource_sum.get('sample_count', '?')} 个样本)"
                        )
                    
                    # 客户端 0 独立审计
                    self.audit_logger.log_client_event(client.cid, tee_id, server_round, report)
                    
                    # 严格拒绝逻辑 (应用 TrustScore & Contribution 熔断)
                    if is_compliant:
                        # [重要] 动态调整参数权重
                        # FinalWeight = TrustScore * ContributionScore
                        final_multiplier = trust_score * contrib_score
                        
                        ndarrays = fl.common.parameters_to_ndarrays(fit_res.parameters)
                        scaled_ndarrays = [layer * final_multiplier for layer in ndarrays]
                        fit_res.parameters = fl.common.ndarrays_to_parameters(scaled_ndarrays)
                        
                        valid_results.append((client, fit_res))
                    else:
                        rejected_count += 1
                        client_logs.append(f"       ❌ 拒绝原因: {reason}")
                    
                except Exception as e:
                    client_logs.append(f"    ⚠️ [Client {client.cid}] 报告解析警告: {e}")
                    valid_results.append((client, fit_res))
            else:
                client_logs.append(f"    ⚠️ [Client {client.cid}] 未附带可信报告")
                valid_results.append((client, fit_res))
            
            # [原子性] 刷新此客户端的缓冲日志
            self.audit_logger.log_batch(client_logs)

        # 更新自适应相似度阈值
        self.contribution_validator.update_threshold_stats(round_positive_sims)

        self.audit_logger.log(f"🛡️  [TMAA Server] 审计结束. 放行 ({len(valid_results)}/{len(results)}), 拒绝 ({rejected_count}).")
        
        return super().aggregate_fit(server_round, valid_results, failures)
