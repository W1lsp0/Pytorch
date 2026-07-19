# PRICAI 2026 Paper 614 审稿报告

## Review setup

- 检测轴：`conference / full-manuscript / ai-ml / standard`
- 评估边界：基于提交的 16 页匿名 PDF；代码尚未公开，未运行复现，也未获得补充标准差、各基线配置或完整 KAN 可视化。
- 中心主张：DUKAN 在 KAN-MCP 基础上加入共享/特定子空间分解和基于 VIB 后验标准差的逐样本模态门控，以提升多模态情感分析性能、解释性和模态污染鲁棒性。
- 可见证据：CMU-MOSI、CMU-MOSEI、CH-SIMS v2 三个基准；与文献结果及 KAN-MCP 复现对比；MOSI 上的组件/超参数消融和 feature-dropout 鲁棒性；效率、门控相关图与 t-SNE。

## Major rejection risks

1. **[Critical，Sec. 3.4、Sec. 5.6] 将 VIB 后验标准差直接称为“aleatoric uncertainty”缺乏理论与校准依据。** `sigma_s`、`sigma_p` 是变分编码器为任务损失与 KL 折衷学习出的潜变量尺度，不自动等于输入模态可靠性或观测噪声。stop-gradient 只阻止 gate 反向更新 covariance branch，但 sigma 仍通过重参数化、KL、单模态和多模态目标训练，因此“pure uncertainty signal”不成立。应明确其只是 learned posterior dispersion，并用已知噪声强度、错误概率、校准曲线和选择性风险验证它能否排序真实可靠性。

2. **[Major，Fig. 2] `rho=-0.95` 基本是门控公式的同义反复，不是有效验证。** gate 由 `softmax(-u/T)` 确定，因此它与 uncertainty 强负相关是设计必然，而非模型发现；该图不能证明 uncertainty 正确。需要展示 `u` 与实际单模态误差、缺失/噪声强度及 corruption 前后变化的关系，并与 entropy、MC dropout、deep ensemble、专用 quality head 等不确定性基线比较。

3. **[Major，Sec. 5.4、Table 6] 鲁棒性实验无法把收益归因于自适应门控。** 只在 MOSI 测试特征上随机置零维度，未报告多个种子/误差条，也未展示 corruption 后各模态的 `u` 和 gate 是否相应变化。Full model 在无污染时本就优于 w/o UAMG，因此污染下的差距可能只是基础精度差，而不是识别坏模态。应报告相对退化、paired uncertainty、gate shift，并测试缺失整模态、时间段遮挡、噪声、错位和真实质量退化。

4. **[Major，Sec. 3.3] 去相关不等于独立或“disentanglement”。** Eq. (9) 仅把 batch 内 shared-specific 线性 cross-correlation 压到零，不能推出统计独立；InfoNCE 对齐也不能保证 shared 只保留跨模态 sentiment consensus。t-SNE 和 silhouette 更不能证明因子语义。应收窄术语为 decorrelated subspaces，或增加 HSIC/MI 估计、cross-modal retrieval、shared/specific swapping、模态预测 probe 和标签/内容 probe。

5. **[Major，Table 1/2] SOTA 比较协议不统一且缺少不确定性。** 除 KAN-MCP 标记为作者复现外，大部分基线显然来自文献报告，可能使用不同文本骨干、特征、二分类零值协议和种子。DUKAN 的提升常只有 0.4--0.8 点，但表中不报告标准差、置信区间或显著性；无法判断是否超过训练波动。应在同一代码、DeBERTa 特征和 split 下复现最强近邻方法，报告每模型至少 5 次均值标准差和配对检验。

6. **[Major，Sec. 5.1] “五项中四项最佳”的叙述混淆了不同证据质量。** MOSI/MOSEI 表把不同来源的结果放在同一排行，并选择有利指标强调；MOSI Acc-7 低于 KAN-MCP，MOSEI Corr 与多个方法近似持平。应强调效应量而不是排名，并进行统一协议的 Pareto 比较。

7. **[Major，Sec. 3.5、全文] “interpretable KAN”是核心定位但没有实际解释验证。** 论文声称可通过 edge-level splines 检查共享/特定通道如何驱动预测，却没有展示任何 spline、局部案例、稳定性、faithfulness 或人类评价。Fig. 2 是 gate，Fig. 3 是 t-SNE，均不是 KAN 决策解释。应给出可读的 edge function、全局/局部贡献，与 SHAP/IG 比较，并验证解释在种子和扰动下稳定。

8. **[Major，Sec. 4、Table 2] CH-SIMS v2 的复现细节严重不足。** 只说明遵循 5/3/2-class 协议，没有给 split、中文文本编码器、声视觉特征、超参数、训练轮数或是否复现 KAN-MCP。因而“language-agnostic”结论不可复核。应单独给出 CH-SIMS v2 完整配置和多种子结果。

9. **[Major，Sec. 3.6] Pareto 更新规则仍不完整。** 式 (18) 后称梯度会被 rescale 到“不小于 naive joint gradient”并乘 `gamma>1`，但没有给 rescale 公式；“amplifies SGD noise and aids generalization”也无直接证据。由于该机制沿用 KAN-MCP，必须明确哪些结果来自 backbone/MMPareto，哪些来自本稿新模块。

## Technical review

### Scope

多模态情感分析、信息瓶颈、不确定性和 KAN 符合 AI 会议范围。三个公开数据集覆盖英语与中文，问题具有标准研究价值。主要问题是“uncertainty-aware”“disentangled”“interpretable”三个关键词都比现有验证更强。

### Novelty

把 IB 后验尺度复用于 gate 是轻量且有吸引力的工程想法，shared/specific 对齐也与 KAN-MCP 形成自然扩展。但 InfoNCE、cross-correlation penalty、softmax uncertainty gate 和 Pareto balancing 均为已有机制，整体更像增量组合。需要精确对比 KAN-MCP、MISA/ConFEDE 及 quality-aware fusion，证明不是常规模块叠加。

### Validity

- 三个模态分别训练的 posterior scale 未必处在可比较标度上；不同 encoder、KL 权重和输入维度会改变 sigma。统一 softmax 前需要校准或归一化论证。
- shared/specific 各只有 2 维，极端瓶颈可能让 t-SNE 结果和分离指标容易出现，且能否表达 modality-specific 结构存疑。
- MOSI batch size 为 8，InfoNCE 只有很少 in-batch negatives，并可能把相同情感样本当 negatives；需要队列/大 batch 控制。
- 对所有 token/frame 做 temporal mean pooling 丢失语言顺序、语音动态和视听对齐，方法实际不是细粒度 multimodal interaction；应明确这是 utterance-level late fusion 的局限。

### Data and experiments

- 所有深入分析都在 MOSI，关键 gate 图却写为 MOSEI；需要在三个数据集一致验证主张。
- Table 3 没有 “UAMG only” 行，不能识别 gate 与两个正则的交互；也缺少简单 learnable gate、fixed gate 和 random gate。
- 超参数敏感性使用同一测试指标展示，若据此判断默认值“最优”，存在测试集调参风险；应只依据 validation 选择，再一次性报告 test。
- robustness 还需要多强度曲线、多个 corruption 类型、统计区间和 robust-fusion baseline。
- Table 7 没有 KAN-MCP、无 UAMG 或其他强基线的参数/速度，因此不能判断新增模块的真实成本；`end-to-end` 也应说明声视觉预提取是否包含在计时内。

### Clarity

方法公式、符号和主干结构总体清楚，消融组织也较完整。需要纠正“Barlow Twins penalty”表述：这里不是标准 Barlow Twins 的跨视图 identity objective，而是 shared-specific cross-correlation 零化。还需避免把二维 t-SNE 可视化写成机制证明。

### Compliance

匿名性未见明显身份泄漏。正文引用和参考文献出现大量绿色/红色 PDF hyperlink 边框，影响出版质量；应使用隐藏边框配置。代码只承诺未来公开，审稿阶段缺少匿名仓库降低可复现性。最终版本应核对数据许可和预训练模型许可。

### Advancement

当前结果显示相对 KAN-MCP 的稳定小幅改进，尤其 MOSEI Acc-7 和 corruption 场景值得进一步验证。但核心机制的语义与解释证据尚未闭合，且统一基线下是否显著仍未知，因此推进程度目前偏增量。

## Presentation and first impression

- **Figures/tables：** Fig. 1 结构完整但在单栏宽度下标签很小；Fig. 2(b) 的强负相关是公式决定，容易给读者造成“经验验证”的误导；Fig. 3 的 t-SNE 点云清楚，但缺少跨种子稳定性。Table 1/2 信息密集、字体偏小。
- **Formatting/notation：** 正文中的引用与交叉引用出现彩色方框；`sd/pd` 与 `d_s/d_p` 记号应统一。Table 7 的 “Non-trainable parameters = 284” 与“pretrained backbones dominate 184.30M”容易误解，需说明哪些 backbone 被微调、哪些特征预提取。
- **Writing：** 整体英文成熟，但反复使用 “pure uncertainty”“genuine per-sample reweighting”“matching intended split”等超出证据的定性结论，应改为可检验、有限的观察。

## Actionable revision plan

1. 重新界定 posterior sigma 的含义，并用真实误差/已知污染强度验证校准与排序能力。
2. 重做 corruption 实验：多种子、误差条、相对退化、gate shift、整模态缺失及强 uncertainty-fusion 基线。
3. 在统一 DeBERTa/特征/split 下复现 KAN-MCP 和最强近邻，报告均值、标准差、效应量与显著性。
4. 补齐 CH-SIMS v2 配置，并在 MOSI/MOSEI/CH-SIMS v2 上一致做关键组件验证。
5. 增加 UAMG-only、learned/fixed/random gate、MI/HSIC、subspace probe 和 swapping 实验。
6. 展示并验证 KAN edge-spline 解释；若不做，应删除“interpretable backbone”的中心主张。
7. 明确 MMPareto rescale 算法、计时边界和全部复现细节，提供匿名代码。
8. 修复 hyperlink 彩框、图表字号和过强表述。

## Likely decision posture

按当前证据，倾向 **弱拒稿至拒稿**。论文组织和实验覆盖优于另外几篇稿件，核心想法也有潜力；但 posterior scale 的“不确定性”解释、SOTA 比较公平性和 KAN 可解释性三条中心主张均未得到充分验证。补齐这些证据后有机会达到可接受水平。该判断不代表程序委员会最终决定。
