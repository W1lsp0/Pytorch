# PRICAI 2026 Paper 577 审稿报告（PRICAI long-paper 校准版）

## Review setup

- 检测轴：`PRICAI conference / long paper / full-manuscript / ai-ml / standard`
- 会议校准：PRICAI 允许应用驱动的多模块系统，不要求每个模块都有独立理论创新；但时间切分、标签可得性、基线输入公平和核心方法可复现必须成立。
- 评估边界：基于提交的 16 页匿名 PDF；专有数据、特征字典、代码、时间切分和漂移日志不可见。
- 中心主张：FinRiskNet 融合静态、时序、交易图和文本信号，通过复合损失、风险归因和 SPR，在信用违约预测中同时提高性能、解释性和漂移适应能力。
- 可见证据：约 50 万记录的专有数据、两个公开表格数据集、五次运行、组件消融、后续季度漂移实验和时间归因扰动。

## 主要审稿问题

1. **[Critical，Sec. 4.1] 60/20/20 划分没有说明时间和借款人隔离。** PD 预测必须避免同一借款人或相邻时间窗跨 train/test，也应避免用未来经济状态帮助过去预测。当前结果可能来自随机记录级划分。应明确 borrower-disjoint 与 out-of-time protocol、观察窗、表现窗和标签成熟期；这是主结果成立的最低要求。

2. **[Critical，Sec. 3.4、Sec. 4.3] SPR 的标签来源和测试边界不明确。** SPR 通过 fine-tuning 最近数据更新参数，但 12 个月违约标签只有表现期结束后才能获得。论文没有说明 detection、adaptation 和 evaluation 是否互斥；如果同一后续季度既用于微调又用于测试，会发生泄漏。应明确这是监督式周期重校准还是无标签 test-time adaptation，并画出时间线。

3. **[Major，Sec. 4.1] 专有多模态数据描述不足。** 缺少独立借款人数、每人记录数、图节点/边、快照频率、文本来源、缺失率、LM 版本、特征时间戳和隐私处理。PRICAI 不要求公开专有数据，但必须提供数据卡和足够的统计摘要，使审稿人判断是否泄漏及是否可复现。

4. **[Major，Table 1] 基线是否获得相同模态不清楚。** 如果 FinRiskNet 使用图、文本和时序，而 XGBoost/FT-Transformer 只获得表格特征，提升可能来自更多信息而非模型。无需复现大量 SOTA，但至少应加入一个相同四模态的 direct-concat/late-fusion 基线，并明确每个基线的输入和调参预算。

5. **[Major，Sec. 3.3] Dynamic Focal Loss 和宏观先验仍不可复现。** `kappa`、`gamma(kappa)`、类别权重、lambda、beta、Beta prior 和 `nu` 未给出。补齐公式和默认值，并增加标准 BCE/focal loss 对照即可；不需要为 PRICAI 构建完整损失理论。

6. **[Major，Sec. 3.3、Table 1] “校准”主张没有直接指标。** Log Loss 有一定概率质量含义，但不足以证明宏观 KL prior 带来校准。建议增加 Brier score 或 ECE 加一张 reliability diagram；若无法补充，将 `calibrated` 改为 `regularized toward historical base rates`。

7. **[Major，Sec. 3.5] 理论分析与实际贡献不匹配。** Proposition 1 未限制参数域却声称损失关于参数 Lipschitz，Theorem 1 又直接假设 smoothness；Remark 1 只是通用 Lipschitz 界，不能证明 SPR 稳定。PRICAI 不强制理论证明，删除或降格为直觉讨论比保留不严谨证明更合适。

8. **[Major，Sec. 4.5] RAM 的证据只覆盖 temporal attribution。** feature、text 和 source contribution 未验证，删除 top visits 还可能产生分布外样本。对于 PRICAI，只需补一个 source ablation/feature deletion 对照，并把“满足监管审计”收窄为“提供分析线索”，不必完成完整监管或专家研究。

9. **[Minor，全文] 高风险信贷场景应简要讨论公平性和治理。** education、occupation 可能是敏感属性代理。PRICAI 稿件至少应在 limitations 中说明群体公平、隐私与人类复核边界；若数据允许，可报告一个分组性能表，但不作为本文必须新增的核心贡献。

## Technical review

### Scope

信用风险、多模态学习、概念漂移和可解释 AI 均符合 PRICAI 范围。问题重要，四模态统一建模具有明确应用动机。

### Novelty

各组件本身并非全新，但统一融合、复合损失和低成本 SPR 的组合可达到 PRICAI 应用型 long paper 的创新门槛。应更清楚地说明与最近多模态信用模型及参数高效重校准的差别，避免声称首次解决所有问题。

### Validity

最大问题是时间协议而非网络结构。另需说明 gate 实际没有直接包含 stable attributes、图和文本如何时间对齐、缺失模态如何处理。完整算法框和参数表即可满足会议复现要求。

### Data and experiments

专有数据规模和五次运行是优点，两个公开集也提供一定外部参照。但公开集的 graph/text 是如何 `approximated` 的完全不清楚，因此只能验证表格迁移，不能作为真实四模态外部验证。建议诚实区分 full-modal proprietary evaluation 和 partial-modal public evaluation。

### Clarity

总体结构、贡献列表和图 2 清楚。`Adapted Transformer`、`macroeconomic prior`、`recent data`、`subsequent quarter` 等关键对象需要具体定义。

### Compliance

匿名性未见明显问题。专有信用数据应补充授权、匿名化和用途边界。代码可以在录用后发布，但匿名伪代码和配置应在审稿阶段足够完整。

### Advancement

若 out-of-time 协议和相同模态基线成立，本文的系统化组合对 PRICAI 具有应用价值。当前无法排除实体/时间泄漏，也无法确认 SPR 是否在独立未来数据上评估，因此核心提升尚不能采信。

## Presentation and first impression

- **Figures/tables：** Fig. 1 偏概念示意，Fig. 3 与 Table 1 信息重复；建议用时间切分图替代其中一个。Table 1/2 小数位过多。
- **Formatting/notation：** `tau_drift`、`s^2` 等未给值；显著性符号只出现在部分指标，正文不要笼统声称全部显著。
- **Writing：** 行文流畅，但监管、校准和稳定性措辞应由对应指标支持。

## Actionable revision plan

1. 明确 borrower-disjoint、out-of-time 和标签成熟协议，拆开 adaptation 与 test 时间块。
2. 给出专有数据卡、四模态构造和每个基线的输入信息。
3. 增加一个相同模态的简单融合基线，并补齐 DFL/KL prior 公式与超参数。
4. 增加 Brier/ECE 中至少一个校准指标，或收窄校准主张。
5. 删除/重写不严谨理论，把版面用于时间线和实现细节。
6. 对 source/feature attribution 增加一个基础 faithfulness 对照，并收窄监管措辞。

## Likely decision posture

按 PRICAI 2026 long-paper 标准，当前仍倾向 **拒稿至弱拒稿**。原因不是模块组合不够新，也不是缺少顶会规模实验，而是 PD 时间切分和 SPR 标签/测试边界没有定义，直接影响全部主结果。若作者能证明当前实验已经 borrower-disjoint、out-of-time，且 adaptation 与 test 完全分离，则论文可上调到边缘接收区间。该判断不代表程序委员会最终决定。
