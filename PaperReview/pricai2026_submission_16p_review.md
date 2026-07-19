# PRICAI 2026 TTFL 审稿报告（PRICAI long-paper 校准版）

## Review setup

- 检测轴：`PRICAI conference / long paper / full-manuscript / ai-ml / standard`
- 会议校准：PRICAI 可接受可信 FL 框架的仿真验证，不强制工业级 TEE 部署或形式化安全证明；但标题/摘要必须准确反映实现层级，威胁模型、攻击指标和基线比较必须自洽。
- 评估边界：基于提交的 16 页匿名 PDF；未运行代码，也未获得攻击脚本、日志、数据划分或真实 TEE 证明材料。
- 中心主张：TTFL 将 TEE-style 准入、运行时监控、长期效用/短期风险双流状态和逐层门控聚合串成 trust-flow，在 Non-IID 与混合攻击下兼顾准确率、ASR 和良性客户端保留。
- 可见证据：CIFAR-10 轻量 CNN、Flower/PyTorch、20 个已准入客户端、30 轮、6 类固定攻击、5 次运行；与 FedAvg、Krum、Trimmed Mean、FLTrust 对比；双流、风险探针、重归一化、异质性和 50% stress 实验。

## 主要审稿问题

1. **[Major，Sec. 4.1、Sec. 5.1] TEE 是标题和核心模块，但当前证据是软件仿真。** 论文描述 device key、PCR chain、quote 和 runtime instruction distribution，实验只报告集中式 Flower/PyTorch 仿真，没有真实 SGX/TrustZone、quote 验证或 enclave overhead。对 PRICAI，这不一定要求补完整硬件原型，但必须明确标注 `TEE-style/simulated attestation agent`，删除已实现真实 trusted execution 的暗示。若能补一个最小 quote-verification 或时间开销原型，会显著增强可信度。

2. **[Critical，Sec. 3 Threat Model 与 Sec. 5.1] 可信执行与部分攻击能力没有闭合。** 如果 enclave 固定训练代码并签名输出，已准入客户端如何执行 sign flipping 或 100x gradient scaling？如果攻击发生在 enclave 外，服务器为何接受未经 enclave 完整性保护的更新？数据/标签投毒在 TEE 下仍可发生，但输出篡改需要另一条路径。应按六类攻击逐项说明攻击者控制数据、代码还是 enclave 外通信，并让实验只覆盖威胁模型允许的行为。

3. **[Critical，Table 2、Fig. 7] ASR 对不同攻击的定义混在一起。** trigger/clean-label/semantic backdoor 可以报告 targeted ASR；sign flipping、gradient scaling、一般 label flipping 更应报告 clean accuracy、loss 或 convergence degradation。当前单一 10.21% ASR 和 Fig. 7 的“untargeted ASR”难以解释。应按攻击类型分表，至少给 clean accuracy、targeted ASR 和 detection round，不必扩大数据集也能修复该问题。

4. **[Critical，Table 2、Table 3] `Perm. FPR` 与基线统计口径不一致。** TTFL 只把永久 BLACKLIST 计为 false positive，不计 SUSPECT、QUARANTINE 或逐层拒绝；Krum 没有永久封禁状态，却被赋予 64.20% FPR。14.79% benign review-trigger rate 说明零永久封禁并非零良性代价。应统一报告每轮 benign rejection/participation loss、隔离持续时间和恢复率；永久封禁率只能作为 TTFL 附加指标。

5. **[Major，Sec. 5.2] 基线偏旧且缺少后门专用防御。** 无需覆盖论文引用的所有方法，但仅 FedAvg、Krum、Trimmed Mean、FLTrust 难以支撑六类攻击优势。建议增加 1--2 个最相关且可公开复现的强基线，例如 FLAME/DeepSight 与一个时序检测方法，并确保使用相同攻击和 clean pool。

6. **[Major，Sec. 5.1] 5,000 张 balanced shared pool 的来源和公平性不清楚。** 论文同时称 50,000 张训练图像分给客户端，又称 5,000 张作为共享参考，未说明是否移除、复制或用于调参。该 pool 占训练集 10%，是重要先验。应画出数据流、给出互斥计数，并增加 `pool=0` 或较小 pool 的一个消融；不需要完整无参考系统，但不能把未测试 fallback 当成已验证贡献。

7. **[Major，Sec. 4.1--4.5] 关键递推和风险探针不足以复现。** Kalman gain/噪声/初始化、Beta reputation 更新、risk normalization、状态阈值、layer sensitivity 三项公式和 `C_base` 等参数不完整。PRICAI long paper 至少应提供一个算法框和完整超参数表；不要求进一步理论证明。

8. **[Major，Sec. 4.4] Eq. (8) 的理论解释不严谨。** HistPerf 是带衰减的 Beta evidence ratio，正文却直接套用一阶 EMA 稳态方差。该分析并非论文成立所必需，建议改为直觉性讨论或补充明确假设，避免把近似写成保证。

9. **[Major，Eq. (1)、Eq. (7)] 优化目标与实际聚合权重不一致。** Eq. (1) 按客户端数据量 `p_k` 加权，Eq. (7) 只按 RawScore 归一化。应说明是否有意改为 trust-weighted objective，并增加保留 `p_k` 的对照或修正目标定义。

10. **[Minor，Sec. 5.2] 50% malicious 超出正文 `<50%` 假设。** 10/20 可保留为 assumption-violating stress test，但不能称为假设范围内或“理论边界证明”；建议修改措辞并说明 peer-consistency 在对半合谋时的限制。

11. **[Minor，Sec. 5.3] edge deployability 结论略强。** 服务器 aggregation 从 2.10 s 增至 4.85 s，当前没有端到端通信或真实设备数据。PRICAI 不强制补真实边缘集群，只需将结论限定为 server-side simulation overhead，并报告 TrustReport 相对原模型更新大小的比例。

## Technical review

### Scope

联邦学习安全、可信 AI 和边缘计算符合 PRICAI 范围。论文抓住了 Non-IID 良性漂移与恶意更新难区分的实际问题，双流状态设计动机清楚。

### Novelty

Kalman trust、Beta/EMA reputation、reference similarity、clipping 和 re-normalization 均为已有构件，但把准入、慢效用、快风险和逐层权限组织成 trust-flow，具有 PRICAI 可接受的系统组合新意。需要用最相关基线和组件对照证明组合价值，不必追求全新理论原语。

### Validity

方法叙事清楚，但 threat model 是当前最大硬伤。另需避免使用密码学意义的 `secure aggregation`：TTFL 必须观察每个客户端更新和两两相似度，与隐藏单客户端更新的 Secure Aggregation 不直接兼容。建议改称 robust/trust-weighted aggregation。

### Data and experiments

五次运行、混合攻击、Non-IID sweep 和组件实验已经具备 PRICAI long-paper 的基本规模。最优先的不是强制增加多个大型数据集，而是拆开攻击指标、统一 FPR、补 1--2 个强基线和 no-attack utility。第二个数据集或更大客户端规模属于加分项。

### Clarity

摘要和引言的 object-condition-harm-method 链完整，流程图较丰富。正文同时称“四 linked stages”和“五-phase loop”，需统一；`TMAA`、`Trust Flow`、`TTFL` 的关系以及 FPR/TPR/ASR 的样本空间应明确定义。

### Compliance

匿名性未见明显问题。代码只称已保存并将在未来发布，没有匿名仓库；PRICAI 可以接受录用后开源，但算法框、参数和攻击定义必须在论文/补充材料中足够复现。

### Advancement

如果威胁模型和指标修正后仍保持优势，双流信誉与逐层门控对 PRICAI 可信 FL 主题具有应用价值。当前结果不能直接支持真实 TEE 或生产边缘部署，但可以支持一个 simulation-based trusted-FL framework。

## Presentation and first impression

- **Figures/tables：** Fig. 1--5 配色统一但概念图偏多、标签较小；Fig. 6 信息过密，Table 2 字号偏小。建议删减一张概念图并加入算法伪代码，把 Fig. 6 拆成两图。
- **Formatting/notation：** 图线主要依靠颜色；Table 2/3 混合不可比指标。`beta_fusion`、`RiskEMA_prev` 等排版需要统一。
- **Writing：** 英文总体流畅，但 `absolute separation`、`theoretical boundary`、`secure aggregation`、`full-process trusted` 应收窄。

## Actionable revision plan

1. 重写 threat-model 表，逐攻击说明 TEE 内外控制能力和更新认证路径。
2. 将 TEE 定位为 simulated/TEE-style，或补一个最小真实证明实验；不要暗示已完成工业部署。
3. 按攻击类型重报 clean accuracy/ASR/detection round，并统一 benign false rejection 口径。
4. 增加 1--2 个后门/时序强基线和 no-attack utility baseline。
5. 明确 5,000 张 clean pool 来源并补一个 pool-size 消融。
6. 增加算法框、完整递推和超参数；重写 Eq. (8) 与 Eq. (1)/(7) 的目标解释。
7. 修正 50% stress、secure aggregation 和部署措辞，精简图表。

## Likely decision posture

按 PRICAI 2026 long-paper 标准，当前倾向 **弱拒稿至边缘接收**。实验规模和组合创新基本达到会议范围，不需要以缺少完整工业 TEE 或多数据集直接否决；但 threat model、ASR 和 FPR 三处影响主结论的自洽性，仍需在录用前解释或修正。如果攻击路径本来就有明确实现、作者能按统一指标重排现有结果并补 1--2 个强基线，判断可以上调到弱接收。该判断不代表程序委员会最终决定。
