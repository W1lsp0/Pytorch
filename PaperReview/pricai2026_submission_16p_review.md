# PRICAI 2026 `pricai2026_submission_16p.pdf` 审稿报告

## Review setup

- 检测轴：`conference / full-manuscript / ai-ml / standard`
- 评估边界：基于提交的 16 页匿名 PDF；未运行代码，也未获得日志、数据划分、攻击脚本、真实 TEE 设备证明或补充材料。
- 中心主张：TTFL 将 TEE 驱动的准入和运行时监控、参考梯度审计、长期效用/短期风险双流状态以及逐层门控聚合串成 trust-flow，在强 Non-IID 和混合投毒/后门下同时保持准确率、低 ASR 与接近零的永久封禁 FPR。
- 可见证据：Flower/PyTorch 上的 CIFAR-10 轻量 CNN 仿真，20 个已准入客户端、30 轮通信、6 个固定攻击客户端、5 次重复；与 FedAvg、Krum、Trimmed Mean、FLTrust 对比；双流、风险探针、重归一化、异质性和 50% 恶意比例实验；服务器聚合耗时与 TrustReport 大小。

## Major rejection risks

1. **[Critical，Sec. 3、Sec. 4.1、Sec. 5.1] TEE 是中心贡献，但实验没有可见的真实 TEE 或远程证明实现。** 方法描述 device-unique key、PCR chain、attestation quote、代码签名和指令分布，实验却只说明 Flower/PyTorch 运行在五张 A10 的服务器仿真上，没有 SGX/TrustZone/TPM 平台、enclave 边界、quote 验证链、密钥管理、TCB、证明延迟、内存限制或失败模式。五个“无有效证书”的 Sybil 节点被拒绝只是预设规则的直接结果，不能验证 TMAA 的真实性或开销。应实现至少一个真实 TEE 原型，或明确把本稿降格为 TEE-inspired simulation；报告 attestation、enclave local training、TrustReport 生成和通信的端到端成本及安全边界。

2. **[Critical，Sec. 3 Threat Model 与 Sec. 5.1] 已证明执行完整性与攻击能力之间存在未解决的威胁模型矛盾。** 若签名的 enclave 代码固定本地训练和输出，已准入客户端如何在 enclave 内执行 sign flipping 或将更新放大 100 倍？若攻击发生在 enclave 外，服务器为何接受被篡改且无法由 enclave 认证的更新？数据投毒/恶意标签在可信代码下仍可能成立，但代码级模型替换与输出缩放需要另一条攻击路径。应为六类攻击逐项列出攻击者控制的资产、是否在 TEE 内、证明覆盖范围和更新签名验证路径，并只保留与模型一致的攻击。

3. **[Critical，Sec. 5.1--5.3、Table 2、Fig. 7] 单一 ASR 混合了语义不同的攻击，主结果无法解释。** label flipping、sign flipping 和 gradient scaling 是非定向可用性攻击，通常用 clean accuracy、loss 或 convergence 衡量；trigger、clean-label、semantic backdoor 才有 target-specific ASR。Fig. 7 甚至把 sign flipping 和 gradient scaling 也标为 ASR。Table 2 的 10.21% 未说明是对哪些触发器、源类/目标类和测试子集求平均。应按攻击逐项报告 clean accuracy、targeted ASR、source-class ASR、worst-case ASR 和检测延迟，混合场景只能作为附加压力测试，不能替代单攻击结果。

4. **[Critical，Table 2、Table 3] FPR 定义在方法间不可比，并通过排除临时隔离低估了良性客户端伤害。** TTFL 的 FPR 只统计不可逆 BLACKLIST，却不把 SUSPECT/QUARANTINE 和被逐层拒绝的良性更新计为误拒；Krum 是每轮选择器，不具有“永久封禁”，却被赋予 64.20% FPR；Trimmed Mean 则记为 N/A。论文另报 14.79% 良性 review trigger rate，说明零永久封禁不等于零业务代价。应采用共同的 per-round false rejection、client-round participation loss、累计权重损失、隔离持续时间和恢复延迟；永久封禁率可作为 TTFL 的附加指标，不能直接与 Krum 选择率比较。

5. **[Major，Sec. 5.2] 基线明显不足，尤其缺少论文自己引用的后门和时序检测方法。** 仅比较 FedAvg、Krum、Trimmed Mean 和 FLTrust，无法支撑“六类混合攻击”和 TEE-trust-flow 的优势。DeepSight、FLAME、FLDetector、CrowdGuard、RoseAgg、ShieldFL 等已在 Related Work 中出现却未实验；也没有单一信誉、逐层 clipping、近期自适应 robust aggregation 的强实现。应在统一数据、攻击强度、clean pool、调参预算下加入最近且公开可复现的 poisoning/backdoor defenses，并分别比较无 clean root 与有 clean root 两种设定。

6. **[Major，Sec. 5.1] 5,000 张 balanced shared pool 的来源和使用方式不清，可能造成不公平或数据复用。** 论文先称 50,000 张 CIFAR-10 训练图像分给 20 个客户端，又称共享 5,000 张作为 common alignment basis，未说明这 5,000 张是否从客户端数据中移除、是否被复制、是否用于调参/风险探针、以及所有基线是否获得相同信息。5,000 张占训练集 10%，是很强的服务器侧可信先验。应给出互斥数据流图、样本计数和 clean-pool size sensitivity，并实验完全无服务器干净数据的 fallback。

7. **[Major，Sec. 4.1、4.5] 多个风险探针依赖未定义或潜在先验信息，难以复现和抵抗自适应攻击。** `Delta_grad`、`Delta_loss`、`instr_dist` 如何离散化成同一熵分布未定义；clean probe、activation histogram、trigger drift 的 probe set、层、bin、归一化和阈值均缺失。若 trigger probe 需要已知触发器，它不能证明对未知 backdoor 有效。应给出完整公式/伪代码、阈值选择集、每个探针可观测信息，并加入 defense-aware adaptive、colluding、low-amplitude、sleeper-burst 和 model-replacement 攻击。

8. **[Major，Sec. 4.1--4.3] 核心状态更新和逐层门控没有达到可复现标准。** Kalman gain、状态转移、过程噪声、测量 `Z_k`、初始化；Beta reputation 的 alpha/beta 递推；risk probes 的归一化；四状态阈值；layer privacy/utility/security 三项的公式与权重；`C_base` 等关键参数均未完整给出。Table 1 只列少量超参数。应提供逐轮算法框、全部递推式、范围约束、默认值和复杂度。

9. **[Major，Sec. 4.4] 分析段把 Beta reputation 与 EMA 低通公式混为一谈。** `HistPerf=alpha/(alpha+beta)` 来自带衰减的 Beta 证据更新，但 Eq. (8) 直接套用一阶 EMA 的稳态方差，未证明该非线性比值满足同一递推和独立同分布噪声假设。该式最多是直觉性近似，不能证明低 FPR。应推导真实更新下的界，明确假设并用仿真验证，或删除理论保证式措辞。

10. **[Major，Sec. 3、Eq. (1)、Eq. (7)] 聚合目标与实际权重不一致。** 系统目标用 `p_k=|D_k|/sum|D_j|`，但逐层 survivor 权重只按 RawScore 归一化，未包含数据量 `p_k`。这改变了所优化的全局目标，也可能让小客户端和大客户端权重失真。应明确这是有意的 robust objective，并给出新的目标/收敛分析，或在可信分数中保留样本量权重并做公平消融。

11. **[Major，Sec. 5.2] 50% 恶意实验超出文中 `<50%` 威胁假设，且没有同条件基线。** 10/20 恶意不是“低于 50%”，只能标为 assumption-violating stress test。单独一行 TTFL 结果也不能证明相对稳定性，特别是 peer consistency 在对半合谋时可能失效。应修正措辞，使用更多客户端测试 45%/49%，并报告协同攻击及强基线曲线。

12. **[Major，Sec. 5.1--5.3] 实验规模不足以支撑 edge deployability 和广泛鲁棒性。** 只有 CIFAR-10、一个轻量 CNN、20 客户端、30 轮和集中式五 GPU 仿真；没有真实边缘设备、掉线/异步、带宽、TEE 内存、FEMNIST/Tiny-ImageNet/CIFAR-100、ResNet 或更多客户端。服务器 aggregation 从 2.10 s 增至 4.85 s，是 131% 增长，不能仅凭“通信通常更慢”断言可接受。应测端到端 round latency、通信量、内存、能耗和不同规模的增长曲线。

## Technical review

### Scope

联邦学习安全、边缘智能和可信执行符合 PRICAI 的 AI/系统交叉范围，问题重要，Non-IID 良性漂移与恶意更新难区分的工程矛盾也建立得较清楚。不过论文同时覆盖 TEE、信誉建模、后门检测、逐层聚合和边缘部署，当前实验只验证了其中的软件仿真部分。

### Novelty

将准入证据、慢速历史效用、快速风险和逐层权限串成 trust-flow 具有系统组合新意，双流设计的动机也合理。但 Kalman trust、Beta reputation、EMA risk、reference similarity、clipping 和重归一化均是已知构件；与最接近的 TEE-FL、FLDetector/temporal reputation、FLAME/DeepSight 和 layer-wise defenses 缺少逐项差异表与受控实验。当前很难判断贡献是新机制还是多个常规模块的工程拼装。

### Validity

- “secure aggregation”一词与算法需求冲突：TTFL 必须观察每个客户端的原始更新、两两余弦和候选更新后的激活；若使用密码学 Secure Aggregation 隐藏单个更新，这些操作不可直接执行。应改称 robust aggregation，或给出兼容的安全多方计算协议。
- TEE 不能判断输入标签是否真实，也不能自动提供 semantic safety。论文应清楚区分 execution integrity、data integrity 和 model-update safety。
- `privacy exposure decays with depth` 和“后门集中在深层”的假设并非普遍成立，且没有逐层实验证据。应报告每类攻击的 layer-wise norm/ASR，并测试相反分布。
- survivor 重归一化本身是过滤后加权平均的标准必要步骤；若对照实现故意不归一化，得到的收敛差距可能只是无效学习率。应与调好学习率的 global clipping 和正确归一化基线比较。

### Data and experiments

- 攻击客户端固定为 0--5，良性异质客户端为 6--19；需要说明攻击者自身的数据分布，并随机化攻击身份，使攻击者也可能持有 alpha=0.1 的长尾数据。
- 六类攻击各只有一个客户端，导致每类检测统计极小；五次 seed 仍不足以支持 0.00% FPR、100% TPR 的确定性表述。应报告 Wilson/bootstrap 区间和更多客户端配置。
- TTFL 的标准差异常小于多数基线，但没有显著性检验或逐 seed 原始值；应给效应量、置信区间和 paired tests。
- 缺少 no-attack utility baseline，无法知道防御在全良性条件下的准确率、收敛和误隔离成本。
- Fig. 8 没有误差条或数值表，`beta_fusion=2.0` “best observed balance”也没有完整 sensitivity 数据。
- 需要按每种攻击分别做 attack-strength sweep，并报告检测时间、首次危害前暴露轮数和自适应规避。

### Clarity

标题、摘要和引言形成了清晰的 object-condition-harm-method 链，四阶段叙事易于理解。主要清晰度问题是流程描述多、算法定义少；“五阶段”Fig. 3 与正文开头“四 linked stages”也不一致。`TMAA`、`Trust Flow`、`TTFL` 的命名关系应统一，`FPR`、`TPR`、`ASR` 应在首次出现时给严格样本空间定义。

### Compliance

匿名格式未见明显身份泄漏。论文只称代码和日志“preserved”，结论写未来发布，没有匿名仓库或可执行补充材料，因此可复现性仍受限。应确认 CIFAR-10、Flower、攻击实现和 TEE 组件的许可，并在最终提交前执行模板、引用和 PDF 合规检查。

### Advancement

若真实 TEE 原型、完整威胁模型和强自适应攻击验证成立，trust-flow 可能对可信边缘 FL 有实用价值。按当前证据，最强结果来自一个小型、强 clean-pool 辅助的仿真，且指标定义偏向本方法，尚不足以证明相对近期防御或真实边缘系统的显著推进。

## Presentation and first impression

- **Figures/tables：** Fig. 1--5 使用统一配色、系统流程直观，但信息重复较多且 Fig. 2、3、5 的小标签在单栏宽度下难读。Fig. 6 同时塞入双轴收敛、节点轨迹和两张 t-SNE，字号过小；Table 2 也被压缩到难以快速扫描。建议减少概念图，把核心算法改为伪代码，并把结果图拆成独立面板。
- **Formatting/notation：** Fig. 8 的 Dirichlet alpha 在 PDF 中显示不够清楚；图线主要靠颜色区分，灰度打印不稳健。Table 2 的 `Perm. FPR` 对不同方法定义不一致，Table 3 又把百分比和秒数放在同一列。部分符号如 `beta_fusion`、`RiskEMA_prev`、`d_k^(l)` 的排版拥挤。
- **Writing：** 英文总体流畅，但“absolute separation”“theoretical boundary”“secure aggregation”“full-process trusted”等措辞过强。结论应明确这是软件仿真，并避免将永久封禁为零等同于良性客户端无损。

## Actionable revision plan

1. 首先重写 threat model 表，逐攻击说明 TEE 内外控制能力、证明/签名路径和可行性；删除不一致的攻击或修改系统设计。
2. 实现真实 SGX/TrustZone/TPM 原型，或把 TEE 主张降为模拟，并报告完整 attestation/runtime overhead。
3. 重新定义评估：按攻击分别报告正确指标，统一所有方法的 false rejection/participation-loss 定义，并增加 no-attack baseline。
4. 明确 5,000 张 clean pool 的互斥来源，重做 pool-size=0/小比例/当前比例实验，验证无 clean-root fallback。
5. 加入 DeepSight、FLAME、FLDetector、CrowdGuard 等强基线和 defense-aware/colluding/sleeper/model-replacement 攻击。
6. 补全 Kalman、Beta、RiskEMA、状态机、逐层 sensitivity 和 clipping 的全部公式、伪代码与参数。
7. 随机化攻击客户端与 Non-IID 分区，扩大客户端/数据集/模型/轮数，并报告置信区间和显著性。
8. 在真实或仿真的异构边缘设备上测端到端时间、通信、内存、能耗和掉线；避免只报告服务器聚合时间。
9. 修正 `<50%` 与 50% stress 的措辞，检查 Eq. (1)/Eq. (7) 权重目标和 Eq. (8) 理论有效性。
10. 精简概念图、拆分 Fig. 6/Table 2、增大字号并增加灰度可辨线型；提供匿名代码与完整日志。

## Likely decision posture

按当前提交证据，倾向 **拒稿/完成根本性系统与实验重构后重投**。最关键的阻碍不是结果数值，而是 TEE 中心贡献没有真实实现证据、威胁模型与若干攻击不闭合，以及 ASR/FPR 的定义使主比较难以成立。双流信誉与逐层门控的动机有潜力，但需要在公平、可复现且与威胁模型一致的协议下重新验证。该判断是有边界的技术风险评估，不代表程序委员会最终决定。
