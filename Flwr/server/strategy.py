"""
==============================================================================
🌐 TMAA_FedAvg — TMAA 增强版联邦平均聚合策略
==============================================================================
职责：
    作为联邦学习服务端的核心聚合引擎，串联以下四大防御阶段：

    阶段 1: 设备完整性评估（硬门禁 + 软感知 → TrustScore）
    阶段 2: 梯度贡献度审查（余弦对齐 + 非线性映射 → ContentScore）
    阶段 3: 双流正交演进（Stream A: HistPerf EMA 更新 / Stream B: RawScore 生成）
    阶段 4: 分层差异化鲁棒聚合（三维敏感度 + 二次归一化 + L2-Norm 动态裁剪）

核心公式：
    ContentScore = √(S_consist × S_contrib)
    RawScore = Trust^α × Content^β × Hist^γ
    ΔW_global^l = Σ_{k∈Φ^l} [ RawScore_k / Σ_{j∈Φ^l} RawScore_j ] × Clip(ΔW_k^l)

作者: Flwr 联邦学习项目
==============================================================================
"""

import json
import numpy as np
from typing import List, Tuple, Dict, Optional

import flwr as fl
from flwr.common import (
    Parameters, FitRes, Scalar,
    ndarrays_to_parameters, parameters_to_ndarrays,
)
from flwr.server.client_proxy import ClientProxy

from audit import AuditLogger
from trust_manager import TrustScoreManager
from contribution import ContributionValidator
from sensitivity import calculate_layer_sensitivities

# 添加 Client 模块路径（用于导入共享的模型定义）
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Client'))
try:
    from model import get_resnet18
except ImportError:
    pass


class TMAA_FedAvg(fl.server.strategy.FedAvg):
    """
    TMAA 增强版 FedAvg 策略

    与传统 FedAvg 的核心差异：
        - 放弃了「一刀切」的全局加权平均
        - 采用「逐层差异化控制 + 二次归一化 + 动态裁剪」的鲁棒聚合机制
        - 通过正交双流架构解耦「历史信誉更新」与「聚合权重计算」
    """

    def __init__(self, proxy_net=None, proxy_testloader=None, noisy_probe_loader=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        def _env_int(name: str, default: int) -> int:
            try:
                return int(os.getenv(name, str(default)))
            except (TypeError, ValueError):
                return default

        def _env_float(name: str, default: float) -> float:
            try:
                return float(os.getenv(name, str(default)))
            except (TypeError, ValueError):
                return default

        # 初始化核心防御组件
        self.trust_manager = TrustScoreManager()           # 信任分管理器
        self.contribution_validator = ContributionValidator()  # 贡献度验证器
        self.audit_logger = AuditLogger()                  # 审计日志记录器
        
        # [Scheme D / G] 服务器端的真理探针与有毒探针
        self.proxy_net = proxy_net
        self.proxy_testloader = proxy_testloader
        self.noisy_probe_loader = noisy_probe_loader
        # 关闭已知触发器模板探针（默认），避免把已知攻击答案写进检测逻辑
        self.enable_known_trigger_probe = os.getenv("ENABLE_KNOWN_TRIGGER_PROBE", "0") == "1"
        if self.enable_known_trigger_probe:
            self.audit_logger.log("    ⚠️ [Probe Policy] 已启用已知触发器探针（研究模式）")
        # 两阶段探针调度：全量轻量筛查 + 部分重探针验证（优先可疑 + 轮换抽检）
        self.heavy_probe_rotate_mod = max(1, _env_int("HEAVY_PROBE_ROTATE_MOD", 5))
        self.heavy_probe_min_risk = _env_float("HEAVY_PROBE_MIN_RISK", 0.45)
        self.heavy_probe_min_report = _env_float("HEAVY_PROBE_MIN_REPORT_RISK", 0.55)
        
        # 记录上一轮的全局模型绝对权重，用于计算各节点的真实更新量 (ΔW)
        self.global_weights_old: Optional[List[np.ndarray]] = None



    def initialize_parameters(
        self, client_manager: fl.server.client_manager.ClientManager
    ) -> Optional[Parameters]:
        """
        初始化全局模型参数。
        因为我们需要截获每一次更新前的绝对权重以求取 Delta W，因此必须在开局时
        在此获得一份与 Client 端一致的初始模型镜像，并存入 self.global_weights_old。
        """
        # 尝试调用基类的方法 (如果配置了 initial_parameters)
        initial_parameters = super().initialize_parameters(client_manager)
        
        # 如果用户没有在 server.py 提供 initial_parameters，我们主动从 Client 仓库的主模型拿一份
        if initial_parameters is None:
            self.audit_logger.log("🛡️  [TMAA Server] 主动获取初始全局模型权重 (ResNet-18) 用于 Delta W 计算...")
            try:
                import torch
                from model import get_resnet18
                net = get_resnet18()
                weights = [val.cpu().numpy() for _, val in net.state_dict().items()]
                self.global_weights_old = weights
                initial_parameters = ndarrays_to_parameters(weights)
                
                # 构建可训练参数掩码 (用于后续剔除 BatchNorm 的 running_mean 和 running_var)
                mask_list = []
                for k, v in net.state_dict().items():
                    is_trainable = "running" not in k and "num_batches" not in k
                    mask_list.append(np.full(v.numel(), is_trainable, dtype=bool))
                self.trainable_mask = np.concatenate(mask_list)
                
            except Exception as e:
                self.audit_logger.log(f"    ❌ 获取初始模型失败: {e}，将回退到第一轮由某个 Client 上报。")
                self.trainable_mask = None
        else:
            self.global_weights_old = parameters_to_ndarrays(initial_parameters)
            # 注意: 如果提供了 initial_parameters，此处可能无法生成 mask，需依赖模型结构
            self.trainable_mask = None

        return initial_parameters

    def aggregate_fit(
        self,
        server_round: int,
        results: List[Tuple[ClientProxy, FitRes]],
        failures: List[str | BaseException],
    ) -> Tuple[Optional[Parameters], Dict[str, Scalar]]:
        """
        核心聚合入口：接收各客户端的训练结果，执行四阶段防御后返回聚合参数。

        参数:
            server_round: 当前联邦学习轮次
            results:      客户端训练结果列表 [(ClientProxy, FitRes), ...]
            failures:     失败的客户端列表

        返回:
            (聚合后的全局参数, 聚合指标字典)
        """
        self.audit_logger.log(
            f"\n🛡️  [TMAA Server] 第 {server_round} 轮 | 审计阶段开始..."
        )

        if not results:
            return None, {}

        # =========================================================================
        # [Scheme F Phase 2: Compute Server-Side Golden Reference Gradient]
        # 使用当前全局权重在防御级验证集上提炼"纯净共识" g_root_clean
        # =========================================================================
        g_root_clean = None
        if self.global_weights_old is not None and hasattr(self, 'proxy_net') and self.proxy_net is not None and self.proxy_testloader is not None:
            self.audit_logger.log("    🧭 [Entropy Shield] 正在启动 Server 黄金数据集提炼绝对纯净共识梯度 (g_root_clean)...")
            try:
                import torch
                import torch.nn as nn
                import torch.optim as optim
                import copy
                
                device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
                temp_net = copy.deepcopy(self.proxy_net).to(device)
                
                params_dict = zip(temp_net.state_dict().keys(), self.global_weights_old)
                state_dict = {k: torch.tensor(v) for k, v in params_dict}
                temp_net.load_state_dict(state_dict, strict=True)
                
                criterion = nn.CrossEntropyLoss()
                optimizer = optim.SGD(temp_net.parameters(), lr=0.01, momentum=0.9)
                
                temp_net.train()
                for images, labels in self.proxy_testloader:
                    images, labels = images.to(device), labels.to(device)
                    optimizer.zero_grad()
                    outputs = temp_net(images)
                    loss = criterion(outputs, labels)
                    loss.backward()
                    optimizer.step()
                
                trained_weights = [val.cpu().numpy() for _, val in temp_net.state_dict().items()]
                delta_w = [w_new - w_old for w_new, w_old in zip(trained_weights, self.global_weights_old)]
                flat_update_clean = np.concatenate([w.flatten() for w in delta_w])
                
                if hasattr(self, 'trainable_mask') and self.trainable_mask is not None:
                    flat_update_clean = flat_update_clean[self.trainable_mask]
                    
                g_root_clean = flat_update_clean
                self.audit_logger.log("    ✅ g_root_clean 提炼成功，共识裁判权已顺利移交给 Server。")
            except Exception as e:
                self.audit_logger.log(f"    ❌ g_root_clean 提炼失败: {e}，将回退到有风险的防线。")
                g_root_clean = None

        # =========================================================================
        # [Scheme I] 混合噪声探针 (Mixed Noise Probe - Cutout)
        # =========================================================================
        # 通过大面积随机遮挡干净图片，测试客户端模型的置信度断层。
        # 后门模型由于特征提取器扭曲（专职等白块），在看到残缺真特征时会发生 Softmax 熵崩溃。
        
        probe_images_multi_aug = None
        probe_labels = None
        trigger_probe_br = None
        trigger_probe_tl = None
        trigger_target_label = 0
        global_probe_entropy = 0.0 # 占位，之后会被各节点的互相排名代替
        
        try:
            if hasattr(self, 'proxy_testloader') and self.proxy_testloader is not None:
                import torch
                from torchvision import transforms
                device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
                
                # 从纯净验证集中抽取一个 Batch (e.g. 64 images)
                clean_images, clean_labels = next(iter(self.proxy_testloader))
                
                # ==================================================================
                # [Scheme J: Multi-Augmented Probe]
                # 针对微小型后门（例如 3x3 触发器）及 Clean Label 后门，实施“多维联合特征切断”。
                # 我们同时剥夺它的“高清边缘”、“真实色彩分布”以及“局部细节”。
                # ==================================================================
                multi_augment = transforms.Compose([
                    # 1. 极其混乱的色彩重映射 (摧毁色块触发器和背景依赖)
                    transforms.RandomApply([transforms.ColorJitter(brightness=0.7, contrast=0.7, saturation=0.7, hue=0.3)], p=0.8),
                    # 2. 高频特征抹除 (让 C1/C2 无法利用清晰的边缘特征苟活)
                    transforms.RandomApply([transforms.GaussianBlur(kernel_size=(5, 9), sigma=(0.5, 3.5))], p=0.8)
                ])
                
                # 3. 再加上大面积的物理 Cutout (在 tensor 的空间域上直接抹黑)
                B, C, H, W = clean_images.shape
                augmented_images = multi_augment(clean_images.clone())
                cut_h, cut_w = int(H * 0.45), int(W * 0.45) # 遮住约 20%的面积
                
                for i in range(B):
                    y = torch.randint(0, H - cut_h + 1, (1,)).item()
                    x = torch.randint(0, W - cut_w + 1, (1,)).item()
                    # 黑色填充，模拟最恶劣的遮挡环境
                    augmented_images[i, :, y:y+cut_h, x:x+cut_w] = 0.0
                
                probe_images_multi_aug = augmented_images.detach().to(device)
                probe_labels = clean_labels.detach().to(device)

                if self.enable_known_trigger_probe:
                    # [Scheme T] 服务端触发器亲和探针：右下角/左上角双触发（可选研究模式）
                    trigger_probe_br = clean_images.clone()
                    trigger_probe_br[:, :, 29:32, 29:32] = 2.5
                    trigger_probe_tl = clean_images.clone()
                    trigger_probe_tl[:, :, 0:3, 0:3] = 2.5
                    trigger_probe_br = trigger_probe_br.detach().to(device)
                    trigger_probe_tl = trigger_probe_tl.detach().to(device)
                
                self.audit_logger.log("    🎭 [Scheme J: Multi-Augmented Probe] 施加了色偏、高斯模糊与残缺组合，准备执行终极断层剥离...")
        except Exception as e:
            self.audit_logger.log(f"    ❌ [Mixed Noise Probe] 探针生成失败: {e}")




        # 存活客户端数据字典: { cid: {所有相关数据} }
        client_data_map: Dict[str, dict] = {}
        client_logs: List[str] = []
        rejected_count = 0
        heavy_probe_count = 0

        # ==================================================================
        # 阶段 1：设备完整性评估与信任分计算
        # ==================================================================
        reference_weight_sum = 0.0
        reference_weighted_sum = None  # 用于 g_root 的参考梯度（排除软隔离节点）
        fallback_weight_sum = 0.0
        fallback_weighted_sum = None   # 防御性回退：若全部软隔离，用全体节点兜底
        reference_clients = 0

        for client, fit_res in results:
            cid = client.cid
            
            # 提前提取真实的客户端 ID 用于日志显示，如果是异常格式则降级使用 cid 截断
            real_client_id = str(cid)[:5]
            if hasattr(fit_res, "metrics") and isinstance(fit_res.metrics, dict):
                real_client_id = fit_res.metrics.get("real_client_id", real_client_id)

            # ---- 阶段 0：黑名单绝对屏障拦截 ----
            if cid in self.trust_manager.blacklist:
                rejected_count += 1
                reason = self.trust_manager.get_blacklist_reason(cid)
                client_logs.append(
                    f"    ⛔ [Client {real_client_id}] 黑名单拦截: 该节点已被系统永久清退 ({reason})"
                )
                continue

            # ---- 解析安全报告 ----
            report = {}
            if "trust_report_json" in fit_res.metrics:
                try:
                    payload = json.loads(fit_res.metrics["trust_report_json"])
                    report = payload.get("trust_report", payload)
                except Exception as e:
                    client_logs.append(f"    ⚠️ [Client {real_client_id}] 报告解析失败: {e}")

            if not report:
                rejected_count += 1
                client_logs.append(f"    ❌ [Client {real_client_id}] 未提供可信报告，直接拦截")
                continue

            # ---- 硬门禁 + 指数衰减惩罚 → TrustScore ----
            m_attest, trust_score = self.trust_manager.evaluate_device_integrity(
                cid, report
            )
            if trust_score <= 0.0:
                rejected_count += 1
                client_logs.append(f"    ❌ [Client {real_client_id}] 信任评估未通过，熔断拦截")
                continue

            # ---- 提取客户端模型参数 ----
            try:
                # client_weights 提取的是本轮客户端经过 SGD 训练后的完整新模型 (W_new)
                client_weights = parameters_to_ndarrays(fit_res.parameters)
                
                # 如果服务端有上一轮的全局模型 W_old，则计算出客户端真实的更新量: ΔW = W_new - W_old
                if self.global_weights_old is not None:
                    # 将 ΔW 作为真正的特征图参与后续的 TMAA 余弦相似度计算与裁剪
                    weights = [w_new - w_old for w_new, w_old in zip(client_weights, self.global_weights_old)]
                else:
                    # 在第一轮还没有全局历史模型时，无奈退化为直接使用 W (或者全 0 的 ΔW)
                    weights = client_weights
                    
                flat_update = np.concatenate([w.flatten() for w in weights])
                
                # ---- 剔除 BatchNorm 统计量 (关键修复) ----
                # torchvision ResNet-18 的 state_dict 包含 running_mean/var 导致非训练参数的漂移掩盖了真实梯度
                # 借助预先计算的训练参数掩码 (self.trainable_mask) 进行过滤
                if hasattr(self, 'trainable_mask') and self.trainable_mask is not None:
                    flat_update = flat_update[self.trainable_mask]

            except Exception as e:
                rejected_count += 1
                self.audit_logger.log(f"    ❌ [Client {real_client_id}] Scheme D 严重异常，参数解析/重载失败: {e}")
                client_logs.append(f"    ❌ [Client {real_client_id}] 参数解析失败: {e}")
                continue

            data_health_audit = report.get("metrics", {}).get("data_health_audit", {})
            feature_summary = data_health_audit.get("feature_summary", {})
            try:
                backdoor_score = float(data_health_audit.get("backdoor_score", 0.0))
            except (TypeError, ValueError):
                backdoor_score = 0.0
            try:
                pixel_mean = float(feature_summary.get("pixel_mean", 0.0))
            except (TypeError, ValueError):
                pixel_mean = 0.0
            try:
                pixel_std = float(feature_summary.get("pixel_std", 0.0))
            except (TypeError, ValueError):
                pixel_std = 0.0
            report_risk = self.trust_manager.compute_report_risk(report)
            risk_ema_prev = self.trust_manager.fetch_risk_ema(cid)
            is_risk_isolated = self.trust_manager.is_risk_isolated(cid)

            # ---- [Scheme I] 混合噪声探针 (Mixed Noise Probe - Cutout) ----
            # probe_loss 字段现在复用为 probe_entropy (Softmax 熵，越高说明模型在残缺图片前越崩溃)
            probe_loss = 0.0
            probe_acc = 0.0
            spectral_score = 0.0
            trigger_br_score = 0.0
            trigger_tl_score = 0.0
            heavy_probed = False
            try:
                rotate_key = int(str(real_client_id))
            except (TypeError, ValueError):
                rotate_key = abs(hash(str(cid)))
            rotate_hit = ((server_round + rotate_key) % self.heavy_probe_rotate_mod) == 0
            should_heavy_probe = (
                probe_images_multi_aug is not None
                and probe_labels is not None
                and (
                    is_risk_isolated
                    or risk_ema_prev >= self.heavy_probe_min_risk
                    or report_risk >= self.heavy_probe_min_report
                    or rotate_hit
                )
            )
            if should_heavy_probe:
                try:
                    heavy_probed = True
                    import torch
                    import torch.nn.functional as F
                    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
                    
                    # 加载客户端发来的当前权重新模型
                    import copy
                    temp_net = copy.deepcopy(self.proxy_net).to(device)
                    params_dict = zip(temp_net.state_dict().keys(), client_weights)
                    state_dict = {k: torch.tensor(v) for k, v in params_dict}
                    temp_net.load_state_dict(state_dict, strict=True)
                    temp_net.eval()
                    
                    # ==============================================================
                    # [Scheme K-A] 中间层激活值截取 Hook
                    # 截取 avgpool 之后的 512 维特征，用于 SVD 谱分析
                    # ==============================================================
                    activation_store = {}
                    def hook_fn(module, input, output):
                        # output: (B, 512, 1, 1) -> flatten -> (B, 512)
                        activation_store['features'] = output.view(output.size(0), -1).detach().cpu()
                    
                    # 注册 Hook：ResNet-18 的 avgpool 层
                    hook_handle = None
                    if hasattr(temp_net, 'avgpool'):
                        hook_handle = temp_net.avgpool.register_forward_hook(hook_fn)
                    elif hasattr(temp_net, 'global_pool'):
                        hook_handle = temp_net.global_pool.register_forward_hook(hook_fn)
                    
                    with torch.no_grad():
                        outputs = temp_net(probe_images_multi_aug) # (B, 10)
                        
                        # 计算 Accuracy
                        _, predicted = torch.max(outputs.data, 1)
                        total = probe_labels.size(0)
                        correct = (predicted == probe_labels).sum().item()
                        probe_acc = correct / total
                        
                        # 计算平均 Softmax 熵
                        probs = F.softmax(outputs, dim=1) # (B, 10)
                        log_probs = F.log_softmax(outputs, dim=1)
                        entropies = -torch.sum(probs * log_probs, dim=1) # (B,)
                        probe_entropy = entropies.mean().item()
                        probe_loss = probe_entropy

                        # 双触发器亲和评分：目标类置信度 + 预测命中率
                        if self.enable_known_trigger_probe and trigger_probe_br is not None and trigger_probe_tl is not None:
                            out_br = temp_net(trigger_probe_br)
                            out_tl = temp_net(trigger_probe_tl)
                            prob_br = F.softmax(out_br, dim=1)
                            prob_tl = F.softmax(out_tl, dim=1)
                            conf_br = prob_br[:, trigger_target_label].mean().item()
                            conf_tl = prob_tl[:, trigger_target_label].mean().item()
                            hit_br = (torch.argmax(out_br, dim=1) == trigger_target_label).float().mean().item()
                            hit_tl = (torch.argmax(out_tl, dim=1) == trigger_target_label).float().mean().item()
                            trigger_br_score = 0.7 * conf_br + 0.3 * hit_br
                            trigger_tl_score = 0.7 * conf_tl + 0.3 * hit_tl
                        
                        # ==============================================================
                        # [Scheme K-A] SVD 谱分析
                        # 正常模型：特征向量在各维度上均匀分布，top-1 占比低
                        # 后门模型：部分维度异常静默/激活，top-1 占比偏高
                        # ==============================================================
                        spectral_score = 0.0
                        if 'features' in activation_store:
                            feat = activation_store['features']  # (B, 512)
                            # 中心化
                            feat_centered = feat - feat.mean(dim=0, keepdim=True)
                            try:
                                U, S, V = torch.svd(feat_centered)
                                # top-1 奇异值占比
                                spectral_score = float((S[0] / (S.sum() + 1e-9)).item())
                            except Exception:
                                spectral_score = 0.0
                        
                        self.audit_logger.log(
                            f"    🎭 [Client {real_client_id}] Scheme K 联合探针 | "
                            f"Acc: {probe_acc:.1%} | H: {probe_entropy:.4f} | "
                            f"SVD_Top1: {spectral_score:.4f}"
                            + (
                                f" | TrigBR: {trigger_br_score:.4f} | TrigTL: {trigger_tl_score:.4f}"
                                if self.enable_known_trigger_probe
                                else ""
                            )
                        )
                    
                    # 清理 Hook
                    if hook_handle is not None:
                        hook_handle.remove()
                    del temp_net
                    del state_dict
                    del outputs
                    if 'features' in activation_store:
                        del activation_store['features']
                    torch.cuda.empty_cache()
                    
                except Exception as e:
                    self.audit_logger.log(f"    ⚠️ [Client {real_client_id}] Scheme K 探针测试失败: {e}")
                    probe_loss = 0.0
                    spectral_score = 0.0
                    trigger_br_score = 0.0
                    trigger_tl_score = 0.0

            # 保存存活客户端的完整数据
            client_data_map[cid] = {
                "client_proxy": client,
                "fit_res": fit_res,
                "flat_update": flat_update,
                "weights": weights,
                "report": report,
                "real_client_id": real_client_id,
                "trust_score": trust_score,
                "tee_id": report.get("header", {}).get("device_id", "Unknown"),
                "backdoor_score": backdoor_score,
                "report_risk": report_risk,
                "risk_ema_prev": risk_ema_prev,
                "heavy_probed": heavy_probed,
                "entropy": self.trust_manager._safe_float(data_health_audit.get("non_iid_entropy", 1.0)),
                "pixel_mean": pixel_mean,
                "pixel_std": pixel_std,
                "probe_loss": probe_loss,
                "spectral_score": spectral_score,
                "trigger_br_score": trigger_br_score,
                "trigger_tl_score": trigger_tl_score,
            }
            if heavy_probed:
                heavy_probe_count += 1

            # ---- 累加门控后的参考权重（用于构建 g_root） ----
            # 说明：参考方向由设备信任分和风险 EMA 共同门控，风险越高权重越小。
            # 同时启用 Hist 软隔离与 Risk 软隔离：任一命中都不参与 g_root 构建。
            compound_weight = trust_score * ((1.0 - risk_ema_prev) ** 2)
            hist_prev = self.trust_manager.fetch_history(cid)
            is_soft_isolated = self.trust_manager.is_soft_isolated(cid)
            is_reference_isolated = is_risk_isolated or is_soft_isolated

            if fallback_weighted_sum is None:
                fallback_weighted_sum = flat_update * compound_weight
            else:
                fallback_weighted_sum += flat_update * compound_weight
            fallback_weight_sum += compound_weight

            if is_reference_isolated:
                if is_risk_isolated and is_soft_isolated:
                    reason = "Hist+Risk 软隔离"
                elif is_soft_isolated:
                    reason = "Hist 软隔离 (正常偏科)"
                else:
                    reason = "Risk 软隔离 (疑似异常)"
                client_logs.append(
                    f"    ℹ️ [Client {real_client_id}] {reason}: Hist={hist_prev:.2f} | "
                    f"RiskEMA={risk_ema_prev:.2f} 降为旁观者 (不参与基准线构建)"
                )
            else:
                if reference_weighted_sum is None:
                    reference_weighted_sum = flat_update * compound_weight
                else:
                    reference_weighted_sum += flat_update * compound_weight
                reference_weight_sum += compound_weight
                reference_clients += 1

        if client_data_map:
            client_logs.append(
                f"    🔬 [Probe Scheduler] HeavyProbe={heavy_probe_count}/{len(client_data_map)} | "
                f"RotateMod={self.heavy_probe_rotate_mod} | "
                f"MinRisk={self.heavy_probe_min_risk:.2f} | MinReportRisk={self.heavy_probe_min_report:.2f}"
            )

        # 批量输出第一阶段日志
        self.audit_logger.log_batch(client_logs)
        client_logs.clear()

        if not client_data_map:
            self.audit_logger.log("    ❌ 本轮无有效客户端，聚合中止。")
            return None, {}

        # ==================================================================
        # 阶段 2：梯度贡献度审查 → ContentScore
        # ==================================================================
        if reference_weight_sum > 0.0:
            g_ref = reference_weighted_sum / reference_weight_sum
            self.audit_logger.log(
                f"    🧭 g_root 构建: 使用 {reference_clients} 个非软隔离节点"
            )
        elif fallback_weight_sum > 0.0:
            g_ref = fallback_weighted_sum / fallback_weight_sum
            self.audit_logger.log(
                "    ⚠️ g_root 构建回退: 全部命中软隔离，临时使用全体节点防止停摆"
            )
        else:
            self.audit_logger.log("    ❌ g_root 构建失败: 有效权重总和为 0，聚合中止。")
            return None, {}
        
        if g_root_clean is not None:
            g_root = g_root_clean
            self.audit_logger.log("    🧭 核心共识 (g_root) 强制切换至: Server 本地纯净数据集先验 (g_root_clean)")
        else:
            g_root = g_ref
            self.audit_logger.log("    ⚠️ 警告: g_root_clean 不可用，回退至存在投毒被把持风险的 g_ref 聚合梯度")
        
        all_s_contents: List[float] = []
        round_positive_sims: List[float] = []

        # 批量进行成对参数比较、贡献度计算与调和融合
        batch_results = self.contribution_validator.evaluate_batch_content_scores(client_data_map, g_root)

        for cid, score_dict in batch_results.items():
            # 存入每个客户端的数据图
            client_data_map[cid]["s_content"] = score_dict["s_content"]
            client_data_map[cid]["s_contrib"] = score_dict["s_contrib"]
            client_data_map[cid]["s_consist"] = score_dict["s_consist"]
            client_data_map[cid]["cos_root"] = score_dict["cos_root"]
            
            cos_root = score_dict["cos_root"]
            if cos_root > 0:
                round_positive_sims.append(cos_root)
            all_s_contents.append(score_dict["s_content"])

        # ==================================================================
        # 阶段 3：双流正交演进
        # ==================================================================
        mu_avg = float(np.mean(all_s_contents)) if all_s_contents else 0.0
        sigma_scale = float(np.std(all_s_contents)) + 1e-6

        # ---- Stream B: 计算综合绝对评分 RawScore (使用旧资历 t-1) ----
        for cid, data in client_data_map.items():
            raw_base = self.trust_manager.calculate_raw_score(
                cid, data["trust_score"], data["s_content"]
            )
            risk_ema_prev = self.trust_manager.fetch_risk_ema(cid)
            risk_factor = max(0.0, (1.0 - risk_ema_prev)) ** self.trust_manager.risk_raw_attenuation_power
            data["raw_score_base"] = raw_base
            data["raw_score"] = raw_base * risk_factor

        # ---- Stream A: 更新历史信誉（仅基于纯净 ContentScore，生成新历史 t） ----
        content_scores = {cid: d["s_content"] for cid, d in client_data_map.items()}
        cos_root_scores = {cid: d["cos_root"] for cid, d in client_data_map.items()}
        report_risks = {cid: d.get("report_risk", 0.0) for cid, d in client_data_map.items()}
        entropies = {cid: d.get("entropy", 1.0) for cid, d in client_data_map.items()}
        probe_losses = {cid: d.get("probe_loss", 0.0) for cid, d in client_data_map.items()}
        heavy_probe_flags = {cid: bool(d.get("heavy_probed", False)) for cid, d in client_data_map.items()}
        spectral_scores = {cid: d.get("spectral_score", 0.0) for cid, d in client_data_map.items()}
        pixel_means = {cid: d.get("pixel_mean", 0.0) for cid, d in client_data_map.items()}
        pixel_stds = {cid: d.get("pixel_std", 0.0) for cid, d in client_data_map.items()}
        trigger_br_scores = (
            {cid: d.get("trigger_br_score", 0.0) for cid, d in client_data_map.items()}
            if self.enable_known_trigger_probe else None
        )
        trigger_tl_scores = (
            {cid: d.get("trigger_tl_score", 0.0) for cid, d in client_data_map.items()}
            if self.enable_known_trigger_probe else None
        )

        # ==================================================================
        # [Scheme S: 梯度符号一致性检测]
        # 计算每个客户端 ΔW 与 g_root_clean 的逐元素符号一致比例
        # 正常节点符号一致性通常 > 0.55；Label Flip 后门节点因系统性反向推力
        # 会导致符号一致性显著偏低（理论可低至 0.45 以下）
        # ==================================================================
        sign_scores = {}
        if g_root_clean is not None:
            root_sign = np.sign(g_root_clean)
            for cid, d in client_data_map.items():
                flat_dw = d.get("flat_update")
                if flat_dw is not None and len(flat_dw) > 0:
                    client_sign = np.sign(flat_dw)
                    # 符号一致比例：两个向量符号相同的元素占比
                    agree = float(np.mean(root_sign == client_sign))
                    sign_scores[cid] = agree
                else:
                    sign_scores[cid] = 0.5  # 中性值

            # 日志输出本轮符号一致性分布
            if sign_scores:
                vals = list(sign_scores.values())
                self.audit_logger.log(
                    f"    📐 [Scheme S] 符号一致性: "
                    f"Min={min(vals):.3f} | Median={float(np.median(vals)):.3f} | Max={max(vals):.3f}"
                )
                # 输出各节点明细（仅显示低于中位数 5% 以上的可疑节点）
                med = float(np.median(vals))
                for cid, sc in sorted(sign_scores.items(), key=lambda x: x[1]):
                    flag = " ⚠️" if sc < med - 0.05 else ""
                    self.audit_logger.log(
                        f"    📐 [Client {cid}] SignConsist={sc:.4f}{flag}"
                    )

        self.trust_manager.update_history(content_scores, mu_avg, sigma_scale, cos_root_scores)

        
        # ==================================================================
        # [Scheme J] 动态离群门限计算 (Median + k*MAD)
        # 优先使用“低风险 + 本轮真实 heavy probe”的基线子集，避免异常节点抬高门限
        # 当基线样本不足时，再回退到全体 EXPOSED heavy-probed 节点
        # ==================================================================
        exposed_probe_values = []
        exposed_probe_records = []  # (probe_loss, risk_ema_prev, cid)
        clean_baseline_values = []
        baseline_risk_cap = max(0.40, self.heavy_probe_min_risk - 0.05)
        for cid, d in client_data_map.items():
            ent = d.get("entropy", 1.0)
            if ent <= 0.95:
                continue
            if not d.get("heavy_probed", False):
                continue

            probe_val = self.trust_manager._safe_float(d.get("probe_loss", 0.0))
            exposed_probe_values.append(probe_val)

            risk_prev = self.trust_manager._safe_float(d.get("risk_ema_prev", 0.0))
            exposed_probe_records.append((probe_val, risk_prev, cid))
            if risk_prev <= baseline_risk_cap:
                clean_baseline_values.append(probe_val)

        baseline_values = []
        source_tag = "InsufficientSamples"
        mad_k = 1.2

        if len(clean_baseline_values) >= 4:
            baseline_values = clean_baseline_values
            source_tag = "CleanBaseline"
            mad_k = 1.2
        elif len(exposed_probe_records) >= 4:
            # 无低风险纯净样本时，改用“低风险分位”回退，避免可疑样本抬高门限。
            # 这比直接使用 Exposed 全体更稳，且对 C2 类持续漂移更敏感。
            low_quantile = 0.35
            take_n = max(4, int(round(len(exposed_probe_records) * low_quantile)))
            low_risk_subset = sorted(exposed_probe_records, key=lambda x: x[1])[:take_n]
            baseline_values = [x[0] for x in low_risk_subset]
            source_tag = f"LowRiskQuantile({take_n}/{len(exposed_probe_records)})"
            mad_k = 1.0
        elif len(exposed_probe_values) >= 3:
            # 极端小样本兜底：仅使用下半区，避免全量回退放大污染。
            sorted_vals = sorted(exposed_probe_values)
            half_n = max(3, len(sorted_vals) // 2)
            baseline_values = sorted_vals[:half_n]
            source_tag = "LowerHalfFallback"
            mad_k = 1.0

        if len(baseline_values) >= 3:
            import statistics
            sorted_vals = sorted(baseline_values)
            median_val = statistics.median(sorted_vals)
            # MAD = Median(|x_i - median|)
            mad_val = statistics.median([abs(v - median_val) for v in sorted_vals])
            # 动态门限 = 中位数 + k * MAD
            dynamic_threshold = median_val + mad_k * max(mad_val, 0.04)
            # 再加一层上限保护，避免 Exposed 样本整体漂移把阈值抬得过高。
            if exposed_probe_values:
                p75_cap = float(np.percentile(exposed_probe_values, 75)) + 0.12
                dynamic_threshold = min(dynamic_threshold, p75_cap)
            self.trust_manager._probe_outlier_threshold = dynamic_threshold
            self.trust_manager._probe_round_median = median_val
            self.trust_manager._probe_round_mad = mad_val
            self.audit_logger.log(
                f"    📊 [Scheme J] 动态离群门限: Median={median_val:.4f} | MAD={mad_val:.4f} | "
                f"Threshold={dynamic_threshold:.4f} | Source={source_tag} | k={mad_k:.2f} "
                f"(Clean={len(clean_baseline_values)}, Exposed={len(exposed_probe_values)})"
            )
        else:
            # 全科生太少，无法形成有效统计，关闭探针惩罚
            self.trust_manager._probe_outlier_threshold = 999.0
            self.trust_manager._probe_round_median = 0.0
            self.trust_manager._probe_round_mad = 0.0
        
        self.trust_manager.update_risk_history(
            report_risks=report_risks,
            cos_root_scores=cos_root_scores,
            content_scores=content_scores,
            entropies=entropies,
            probe_losses=probe_losses,
            spectral_scores=spectral_scores,
            pixel_means=pixel_means,
            pixel_stds=pixel_stds,
            trigger_br_scores=trigger_br_scores,
            trigger_tl_scores=trigger_tl_scores,
            global_probe_loss=global_probe_entropy,
            sign_scores=sign_scores,
            heavy_probe_flags=heavy_probe_flags,
        )

        # ==================================================================
        # 风险可疑池面板：即使未封禁，也输出“怀疑度”与状态
        # ==================================================================
        suspect_rows = []
        suspect_cnt = 0
        quarantine_cnt = 0
        suspect_risk_floor = max(0.50, self.trust_manager.risk_soft_threshold - 0.05)
        for cid, data in client_data_map.items():
            detail = self.trust_manager.fetch_risk_detail(cid)
            risk_ema = detail["risk_ema"]
            peer_risk_ema = detail.get("peer_risk_ema", 0.0)
            soft_streak = detail["risk_soft_streak"]
            hard_streak = detail["risk_hard_streak"]
            is_quarantine = detail["risk_isolated"]
            if is_quarantine:
                status = "QUARANTINE"
                quarantine_cnt += 1
            elif soft_streak > 0 or risk_ema >= suspect_risk_floor or peer_risk_ema >= suspect_risk_floor:
                status = "SUSPECT"
                suspect_cnt += 1
            else:
                status = "NORMAL"

            suspect_rows.append(
                (
                    risk_ema,
                    peer_risk_ema,
                    soft_streak,
                    hard_streak,
                    data.get("real_client_id", str(cid)[:5]),
                    status,
                    data.get("probe_loss", 0.0),
                    data.get("heavy_probed", False),
                )
            )

        suspect_rows.sort(key=lambda x: (x[0], x[1], x[2], x[3]), reverse=True)
        board = [
            f"    🧪 [Suspect Pool] NORMAL={len(client_data_map)-suspect_cnt-quarantine_cnt} | "
            f"SUSPECT={suspect_cnt} | QUARANTINE={quarantine_cnt} | "
            f"BLACKLIST={len(self.trust_manager.blacklist)}"
        ]
        for row in suspect_rows[:8]:
            board.append(
                f"    🧪 [Client {row[4]}] State={row[5]} | "
                f"RiskEMA={row[0]:.3f} | PeerRiskEMA={row[1]:.3f} | "
                f"SoftStreak={row[2]} | HardStreak={row[3]} | "
                f"ProbeLoss={row[6]:.4f} | HeavyProbed={'Y' if row[7] else 'N'}"
            )
        self.audit_logger.log_batch(board)

        # ==================================================================
        # 阶段 4：分层差异化鲁棒聚合
        # ==================================================================
        sample_weights = next(iter(client_data_map.values()))["weights"]
        num_layers = len(sample_weights)

        # ---- 计算逐层参考梯度（信任加权） ----
        g_ref_layers = []
        layer_trust_sum = (
            sum(data["trust_score"] for data in client_data_map.values()) + 1e-9
        )
        for i in range(num_layers):
            layer_sum = sum(
                data["weights"][i] * data["trust_score"]
                for data in client_data_map.values()
            )
            g_ref_layers.append(layer_sum / layer_trust_sum)

        # ---- 获取三维层级敏感度指纹 ----
        layer_sensitivities = calculate_layer_sensitivities(
            client_data_map, g_ref_layers
        )

        # 初始化全局聚合累加器（全零，强制浮点型以避免累加时类型转换失败）
        aggregated_ndarrays = [np.zeros_like(layer, dtype=np.float64) for layer in sample_weights]
        
        # 统计审计信息：记录每个客户端的逐层被采纳情况
        # 结构: cid -> { "included": 0, "excluded": 0, "avg_clip_scale": 0.0 }
        client_layer_stats = {cid: {"included": 0, "excluded": 0, "sum_scale": 0.0} for cid in client_data_map}

        # ---- 逐层执行「门控过滤 + 二次归一化 + 动态裁剪」 ----
        for l_idx, layer_sens in enumerate(layer_sensitivities):
            threshold_l = layer_sens["inclusion_threshold"]
            clip_target = layer_sens["clip_target"]

            # 步骤 1: 筛选幸存者集合 Φ^l
            # 只有绝对分 RawScore ≥ 该层门槛的节点才有资格参与聚合
            survivors = [
                cid for cid, data in client_data_map.items()
                if data["raw_score"] >= threshold_l
            ]

            # 统计 Excluded
            for cid in client_data_map:
                if cid not in survivors:
                    client_layer_stats[cid]["excluded"] += 1

            if not survivors:
                # 该层无人达标，保留全零（不更新）
                continue

            # 步骤 2: 二次归一化（解决分母缺失问题）
            # 被淘汰节点的权重不会凭空消失，幸存者自动填补，权重总和恢复为 1
            sum_raw_survivors = sum(
                client_data_map[cid]["raw_score"] for cid in survivors
            ) + 1e-9

            # 步骤 3: 对每个幸存者执行动态裁剪并加权累加
            for cid in survivors:
                data = client_data_map[cid]

                # 局部归一化权重
                normalized_weight = data["raw_score"] / sum_raw_survivors

                # 提取该层梯度
                layer_grad = data["weights"][l_idx]
                norm_layer = float(np.linalg.norm(layer_grad))

                # 动态 L2-Norm 裁剪
                # 敏感度越高 → clip_target 越小 → 裁剪越严格
                # 比喻: "进了核心机密室，但笔被换成了极细铅笔"
                scale = max(1.0, norm_layer / clip_target)
                clipped_grad = layer_grad / scale
                
                # 统计 Included 和 裁剪严厉程度
                client_layer_stats[cid]["included"] += 1
                client_layer_stats[cid]["sum_scale"] += scale

                # 加权累加到全局聚合结果
                aggregated_ndarrays[l_idx] += clipped_grad * normalized_weight

        # 生成本轮逐层处理的审计面板日志
        audit_panel = [
            f"    ┌{'─'*65}┐",
            f"    │  🔍 本轮客户端逐层聚合审计面板 (Total Layers: {num_layers:02d})             │",
            f"    ├{'─'*65}┤",
            f"    │  [CID真实编号] | 采纳层数 | 被拒层数 | 平均裁剪力度(Scale) │"
        ]
        
        for cid, stats in client_layer_stats.items():
            inc = stats["included"]
            exc = stats["excluded"]
            # avg_scale = 1.0 意味着完全没被裁剪
            avg_scale = stats["sum_scale"] / inc if inc > 0 else 0.0
            
            # 提取 payload 里包含的真实客户端 ID
            real_id = client_data_map[cid].get("real_client_id", str(cid)[:5])
            short_cid = f"Client {real_id}"
            
            # 高亮显示被拒绝过的或者是被极为严重裁剪的 (考虑到预训练权重的范数放大，阈值放宽到 20.0 倍)
            # 修复: 只有当一轮中大部分层被拒绝，或者平均 Scale 裁剪极其严重时才打警告
            # 否则像 Client 10 这种正常 Non-IID 只是极少数特征层离群，不该被标记为 ⚠️
            is_warn = (exc > inc * 2) or (avg_scale > 20.0) 
            flag = "⚠️" if is_warn else "✅"
            
            audit_panel.append(
                f"    │  {flag} {short_cid:<11} | Inc: {inc:03d} | Exc: {exc:02d} | Scale: {avg_scale:6.2f}x{' '*6}│"
            )
            
        audit_panel.append(f"    └{'─'*65}┘")
        # 直接输出这块面板到日志
        self.audit_logger.log_batch(audit_panel)

        # ==================================================================
        # 日志汇总与结果返回
        # ==================================================================
        # 恢复原始数据类型
        aggregated_ndarrays = [
            arr.astype(orig.dtype) for arr, orig in zip(aggregated_ndarrays, sample_weights)
        ]

        valid_results = []
        for cid, data in client_data_map.items():
            fit_res = data["fit_res"]
            fit_res.parameters = ndarrays_to_parameters(data["weights"])
            valid_results.append((data["client_proxy"], fit_res))

            h_perf = self.trust_manager.fetch_history(cid)
            risk_ema = self.trust_manager.fetch_risk_ema(cid)
            real_id = data.get("real_client_id", str(cid)[:5])
            client_logs.append(
                f"    🌟 [Client {real_id}] "
                f"S_contrib={data.get('s_contrib', 0.0):.3f} | S_consist={data.get('s_consist', 0.0):.3f} | "
                f"Hist={h_perf:.3f} | "
                f"RiskEMA={risk_ema:.3f} | "
                f"ProbeLoss={data.get('probe_loss', 0.0):.4f}"
            )

        self.audit_logger.log_batch(client_logs)
        # 暂不需要在这一步处理历史统计记录
        # self.contribution_validator.update_threshold_stats(round_positive_sims)
        self.audit_logger.log(
            f"🛡️  [TMAA Server] 第 {server_round} 轮聚合完成 | "
            f"存活节点: {len(valid_results)} | 拦截: {rejected_count} | GlobalProbeEntropy: {global_probe_entropy:.4f}"
        )

        # ==================================================================
        # 重建全局模型 W_new = W_old + ΔW_global
        # ==================================================================
        if self.global_weights_old is not None:
            new_global_weights = [
                old_w + delta_w 
                for old_w, delta_w in zip(self.global_weights_old, aggregated_ndarrays)
            ]
        else:
            # 第一轮时，提取出来的本来就是绝对权重，直接继承
            new_global_weights = aggregated_ndarrays
            
        # 保存这轮生成的全局模型供下一轮作减法参考使用
        self.global_weights_old = new_global_weights

        return ndarrays_to_parameters(new_global_weights), {}
