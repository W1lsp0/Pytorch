# PRICAI 2026 Paper 511 审稿报告（PRICAI long-paper 校准版）

## Review setup

- 检测轴：`PRICAI conference / long paper / full-manuscript / ai-ml / standard`
- 会议校准：PRICAI 接受 AI 应用型和组合型创新，不要求顶会规模或临床部署完成度；但独立测试、无明显泄漏、指标解释正确和人体数据合规仍是硬门槛。
- 评估边界：基于提交的 16 页匿名 PDF；未运行代码，未获得数据清单、患者标识、划分文件、伦理批件或补充材料。
- 中心主张：IIEViT-ROI 通过肺区 ROI 门控、VGG19 多尺度特征和 CNN-ViT 交叉注意力，在胸片多分类中取得较好的准确率、速度、解释性和跨域适应能力。
- 可见证据：3 个公开数据集及合并集、3 个复现基线、110 张本地临床子集、模块消融、混淆矩阵和 GPU 批量延迟。

## 主要审稿问题

1. **[Critical，Sec. 3.1] 最终性能没有独立测试集。** 公开数据只做 80:20 train-validation 划分，validation 同时用于 early stopping 和最终报告，每项结果还是单次运行。这是主结果有效性问题，不是会议档次问题。建议保留独立 test split，或至少使用患者级交叉验证并把模型选择与最终评估分开，报告 3--5 次运行的均值和标准差。

2. **[Critical，Sec. 3.1] 图像级随机划分和未去重合并集存在医学影像泄漏风险。** 论文明确没有做跨数据集重复移除，也未说明同一患者多张影像是否跨集合。应按患者/检查分组，进行重复和近重复检测，并给出每个来源的患者数、排重数量及标签映射规则。

3. **[Critical，Sec. 3.3、Table 2] 微调后的“Test With All Clinical Dataset”可能包含微调样本。** 若模型在临床子集上 fine-tune，再在全部 110 张图像上报告 96.36%，该指标不能作为外部泛化证据。应只报告完全未参与微调的 held-out clinical test；样本较少时可用分层交叉验证，但不能把训练样本重新计入测试。

4. **[Major，Sec. 3.3] 卡方和 Fisher 检验没有证明模型优于 X-Vision。** 这些检验只表明预测与标签有关，不能比较两个分类器。PRICAI 不要求复杂统计体系，但至少应在同一测试样本上报告 bootstrap 区间或 McNemar 检验，并删除“统计显著证明优越性”的误读。

5. **[Major，Sec. 2、Sec. 4、Table 3] ROI 和可解释性结论强于证据。** U-Net 的训练来源、Dice/IoU 和失败案例未报告；attention overlay 只有定性展示。Table 3 中去掉 ROI 后，两个公开数据集的 accuracy 反而略高于完整模型，与“完整模型始终最强”冲突。对 PRICAI，补充分割性能、若干代表性失败案例和一个简单的遮挡/删除 faithfulness 测试即可；如果无法补充，应把主张收窄为 ROI-guided visualization，而不是 clinically meaningful explanation。

6. **[Major，Sec. 3、Table 1] 基线与运行波动仍不够充分。** IEViT 和 X-Vision 是作者重写且原始划分未知，当前比较只能视为内部复现。无需覆盖所有医学影像 SOTA，但建议增加 1 个公开、近期且可复现的强 CNN/ViT 基线，并对 proposed 和主要基线使用相同划分、增强和 3--5 个种子。

7. **[Minor，Sec. 3.1] “部署/实时”措辞应限定在当前 GPU 吞吐设置。** 0.88--1.16 ms 来自 RTX A4000、batch size 16，不代表单病例或边缘设备延迟。无需为 PRICAI 强制补完整边缘部署，只需报告 batch=1、说明 ROI/预处理是否计时，并改成 `GPU batch inference efficiency`。

8. **[Major，Sec. 3.3] 人体数据合规信息不足。** 六家机构的图像仅说明科室负责人许可、口头同意和匿名化，没有伦理委员会/IRB 审批或豁免编号。审稿版可匿名化机构，但应提供可核验的审批/豁免说明和口头同意依据。

## Technical review

### Scope

胸片分类、可信 AI 和高效混合网络符合 PRICAI 的 AI 应用范围。低资源医疗场景明确，工程动机充分。

### Novelty

ROI-gated tokenization 与交替 CNN-ViT cross-attention 的组合具有中等工程新意，达到 PRICAI 应用论文可讨论的水平。无需证明顶会式全新范式，但应通过更明确的替代消融区分固定 ROI enhancement、可学习 gate 和 cross-attention 的作用。

### Validity

方法整体可理解，但 gate 的完整公式、两个 CNN token 的构造、辅助损失、差分学习率和 residual scaling 仍不够明确。补一个算法框和完整超参数表即可显著提高可复现性。

### Data and experiments

数据量和三个公开集对 PRICAI 已有竞争力，主要缺口不是规模，而是划分可信度。修复患者级划分、独立测试和临床样本复用，比继续增加数据集更重要。医疗分类最好同时报告类别级 recall/specificity 或 AUROC，但不要求构建完整临床验证体系。

### Clarity

摘要、引言和贡献链条清楚，也主动承认临床样本较小。结果段仍频繁使用 `robust`、`validating adaptability`、`deployment` 等强词，应与回顾性验证边界一致。

### Compliance

双盲外观基本合格，匿名代码链接需确认不泄露身份。伦理审批信息是主要合规问题。页数和 LNAI 版式符合 long-paper 形态。

### Advancement

在 PRICAI 应用论文标准下，方法组合和速度结果具有潜在价值；但当前泄漏风险使数值优势无法可靠解释。修复评估协议后，即使准确率不是全部最优，也可能凭效率与结构设计形成贡献。

## Presentation and first impression

- **Figures/tables：** Fig. 1 信息密度过高且字号偏小；Fig. 2 类名拥挤。建议简化架构图并拆分性能与效率表。
- **Formatting/notation：** 页眉出现 `Title Suppressed Due to Excessive Length`，应设置 short title；`Inf.(ms)` 要注明 batch-amortized per-image latency。
- **Writing：** 英文可读，但存在局部语法和标点问题；临床使用措辞应统一为 retrospective screening research。

## Actionable revision plan

1. 建立患者级、去重且独立的 test protocol，重跑主表并报告运行波动。
2. 删除含微调样本的临床全集指标，只保留 held-out 或交叉验证结果。
3. 补齐伦理审批/豁免信息和数据纳排规则。
4. 补 1 个强公开基线，并修正统计检验的解释。
5. 报告 ROI 分割质量和一个基础 faithfulness 测试，或收窄解释性主张。
6. 修正 batch latency、页眉、图表字号和过强临床措辞。

## Likely decision posture

按 PRICAI 2026 long-paper 标准，当前倾向 **弱拒稿至拒稿**。方法与实验规模本身基本匹配会议，决定性问题是患者级泄漏风险和临床样本复用，而不是缺少顶会级实验。若划分本来就是患者互斥且作者能提供证据、并删除无效的临床全集评估，则判断可明显上调。该判断不代表程序委员会最终决定。
