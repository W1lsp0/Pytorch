# PRICAI 2026 Paper 577 审稿报告

## Review setup

- 检测轴：`conference / full-manuscript / ai-ml / standard`
- 评估边界：基于提交的 16 页匿名 PDF；专有数据、代码、特征字典、时间切分清单和补充实验均不可见。
- 中心主张：FinRiskNet 统一融合静态、时序、交易图和文本四种信用风险模态，通过复合损失、风险归因模块和选择性参数重校准，同时提升 PD 预测、可解释性和概念漂移适应能力。
- 可见证据：一个约 50 万记录的专有数据集、两个公开表格数据集；60/20/20 划分；五次种子实验；组件消融、一个后续季度的漂移模拟、单病例解释和时间归因扰动。

## Major rejection risks

1. **[Critical，Sec. 4.1] 数据划分没有时间和借款人隔离定义，无法支撑 PD 或漂移结论。** 论文只写 60/20/20 train/validation/test，没有说明是随机、按时间、按借款人还是按账户划分。一个借款人的滑窗记录若跨集合出现，会产生实体泄漏；随机切分也会把未来经济状态泄露给过去。应使用 borrower-disjoint 的 out-of-time 测试，明确观察窗、表现窗、标签成熟期、删失处理和各时间段。

2. **[Critical，Sec. 3.4、Sec. 4.3] “Test-Time Adaptation” 的标签与评估协议未定义。** SPR 通过 fine-tuning 最近数据来更新参数，但没有说明最近数据是否已有违约标签、哪些样本用于漂移检测、适应和最终测试。PD 的 12 个月标签只有经过表现期才能获得，因此这不是通常意义上的即时测试时无标签适应；若用同一后续季度标签适应并评估，则构成测试泄漏。应明确将方法命名为监督式在线/周期重校准，或者给出真正无标签目标；用互斥的 detection/adaptation/evaluation 时间块做 prequential 评估。

3. **[Major，Sec. 4.1] 专有多模态数据描述不足，实验不可审计。** 缺少借款人数、每人记录数、缺失率、图节点/边定义、图快照频率、文本来源与长度、LM 具体版本、特征时间戳、标签定义、纳排标准和隐私治理。约 50 万“records”无法判断是否对应独立样本。应提供匿名化数据卡、特征构建时间线、伪代码和足以复现实验的统计摘要。

4. **[Major，Sec. 4.1、Table 1] 基线比较可能混入模态优势，公平性没有建立。** FinRiskNet 使用完整图、文本和时序信号，而 Logistic Regression、XGBoost、FT-Transformer、Temporal CNN 和“Adapted Transformer”各自获得哪些输入没有说明；也没有多模态 GNN/时序图网络、late fusion、TFT、完整 retraining/rolling-window 等强基线。若基线只看表格特征，则提升不能归因于架构。应让基线获得相同信息和调参预算，并分别报告 same-modality 与 production-baseline 两组比较。

5. **[Major，Sec. 3.3] Dynamic Focal Loss 不可复现且论证不完整。** 关键的 batch separability `kappa` 和 `gamma(kappa)` 没有定义，类别权重、lambda、beta、Beta prior 参数与 concentration `nu` 也未给出。以 mini-batch 统计动态调整 gamma 会导致强烈 batch-size 依赖。应给出完整公式、范围、稳定性处理和每一损失项的受控消融。

6. **[Major，Sec. 3.3、Table 1] “校准”主张没有校准证据。** 把每个预测构造成 Beta 分布并向宏观基准率 Beta prior 做 KL，可能将个体 PD 收缩到总体基准率，但不等价于概率校准。论文只报告 Log Loss、MAE、AUROC，没有 Brier score、ECE、自适应校准误差或 reliability diagram，也没有与 Platt/isotonic/temperature calibration 比较。应补充 out-of-time 分层校准评估，并检验经济周期和风险群体下的稳定性。

7. **[Major，Sec. 3.5] 理论结果没有为所提方法提供实质保证。** Proposition 1 在未约束网络权重的情况下不能仅由输入有界推出损失关于参数全局 Lipschitz；其后 Theorem 1 又直接假设 L-smooth，与前述 Lipschitz continuity 不是同一性质。Remark 1 的式 (19) 只是 Lipschitz 定义的直接应用，不能推出 SPR 保持性能或比 full fine-tuning 稳定。应严格补齐参数域和梯度界，或删除与方法贡献无关的通用 SGD 收敛段落。

8. **[Major，Sec. 3.4] 漂移检测器不能识别一般概念漂移。** 预测分布的 JS 变化只观测边际输出分布，可能把先验变化、样本构成变化和模型漂移混为一谈，也可能漏掉 `P(y|x)` 改变但输出边际近似不变的情况。阈值 `tau_drift` 的选择、误报/漏报、检测延迟均未报告。应与 ADWIN、DDM/Page-Hinkley、定期重训和无检测器策略比较，并构造多类真实/合成漂移。

9. **[Major，Sec. 4.5] RAM 仅验证了时间路径的一小部分，不能支撑“可审计解释”。** temporal attention、Integrated Gradients 和线性化 source contribution 是三种不同机制；当前扰动实验只删除 top visits，而且删除会产生分布外序列。没有验证 feature/text/source attribution 的 completeness、稳定性、敏感度或人类可理解性。应加入随机/连续遮挡、ROAR/KAR、IG 收敛、source ablation 和领域专家盲评，并避免把 attention 直接当解释。

10. **[Major，全文] 高风险信贷应用缺少公平性、合规和治理评估。** 稳定属性包含 education、occupation 等可能构成代理变量，但论文没有群体公平性、拒贷影响、漂移后差异表现、隐私、申诉和人类复核分析。解释性不能自动满足监管要求。至少应按可用人口群体报告校准、TPR/FPR 和误差区间，并阐明数据处理和使用边界。

## Technical review

### Scope

信用风险、多模态学习、可解释性和持续适应符合 AI 会议范围，问题也具有明显工程价值。但论文同时提出架构、损失、归因、漂移适应和理论五条贡献，在 16 页内每条都验证不足，导致范围过宽而证据过浅。

### Novelty

门控多模态融合、Transformer、focal loss、attention/IG 解释和局部参数微调均是已知技术。潜在新意在于将这些机制统一用于 PD 并设计 SPR，但 Related Work 没有精确比较最近的多模态信用模型、时序图信用模型和参数高效持续学习；“四种模态首次统一”的优先权缺乏系统证据。需要以最近邻方法表清楚区分输入、适应方式和解释层级。

### Validity

- Eq. (5)--(6) 的 gate 是对融合向量逐元素缩放，而不是明确的四模态权重；stable attributes 又在 readout 时单独拼接，所谓“四模态统一门控”不准确。
- 图与文本表示只给抽象公式，未说明时间对齐、缺失模态、冻结/微调和泄漏防护。
- PDS 使用“recent validation holdout”，实际部署中持续可用的验证标签及维护机制没有定义。
- 五个种子的 paired t-test 样本量很小；需要说明配对单位、同一 split/seed 对齐、效应量和多重比较处理。

### Data and experiments

- 两个公开表格数据集没有原生图、文本和月度序列，论文称其由 derived features “approximated”，却没有定义构造方法。这些结果不能验证真实多模态融合的外部泛化。
- 对 3.2% 默认率只报 AUROC 不足，应加入 AUPRC、recall@fixed-FPR、KS、Brier、分箱校准和经济成本。
- “后续经济季度”没有起止时间、宏观变化、样本量和默认率，也没有多窗口结果。
- 缺少模型参数量、训练/推理成本、硬件与 wall-clock；Table 3 的 `0.31x` 未说明测量方法。
- 需要跨机构或至少多时间段验证，而不是只在一个专有来源上验证完整四模态模型。

### Clarity

问题动机、模块命名和总体结构较清楚，图 2 也便于理解。但抽象层次远高于实现层次，大量关键对象仅用名称代替定义，例如 “Adapted Transformer”“macroeconomic prior”“recent data”“subsequent quarter”。这些缺口直接妨碍技术核验。

### Compliance

专有信用数据未提供伦理/隐私审批、数据处理协议、匿名化、合规依据或利益冲突信息。最终稿需要明确数据来源授权和高风险自动决策边界。匿名格式本身未见明显作者身份泄漏。

### Advancement

如果协议完整且结果可复现，统一建模与低成本重校准可能有实际价值。目前提升无法从更多模态、数据泄漏、随机切分和模型设计之间解耦，理论与解释证据也不足，因此尚不能确认显著推进。

## Presentation and first impression

- **Figures/tables：** Fig. 1 偏概念营销图，不能替代技术流程；Fig. 2 可读但没有张量尺寸、时间轴和缺失模态路径。Fig. 3 把 Table 1 数字再画成柱状图，信息重复。Table 1/2 字号较小且多项小数精度过高。
- **Formatting/notation：** 理论部分同时使用 Lipschitz、L-smooth 等概念但定义不一致；`s^2`、`tau_drift` 等关键量缺少取值。表格中的显著性符号只出现在部分指标，正文却笼统声称所有改进显著。
- **Writing：** 行文流畅，但多处把监管可解释性、校准和稳定性当作模块存在即可成立，应改成由指标和验证支持的有限主张。

## Actionable revision plan

1. 首先固定 borrower-disjoint、out-of-time、标签成熟的评估协议，并画出 observation/adaptation/evaluation 时间线。
2. 明确 SPR 使用标签还是无标签；拆开漂移检测集、适应集和最终测试集，加入多窗口及检测基线。
3. 发布可审计的数据卡和完整实现细节，特别是四模态构造、时间戳和公开数据的伪模态生成。
4. 在相同模态和调参预算下重做强基线，并补 AUPRC、Brier、ECE、业务阈值和公平性指标。
5. 完整定义 DFL/KL prior 的所有函数与超参数，加入标准 focal/class-balanced/calibration 基线。
6. 重写或删除泛化理论，避免用通用假设包装经验观察。
7. 对三类归因分别做 faithfulness、稳定性和专家验证；收窄监管合规措辞。
8. 报告参数、硬件、训练与适应耗时，并公开匿名代码或可执行补充材料。

## Likely decision posture

按当前稿件，倾向 **拒稿/大幅补充协议与证据后重投**。核心阻碍是时间与实体切分、SPR 标签可得性和专有多模态数据均未定义，因而主结果、漂移适应和解释性无法独立核验。该判断是审稿风险姿态，不代表程序委员会最终决定。
