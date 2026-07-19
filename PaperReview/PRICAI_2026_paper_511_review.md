# PRICAI 2026 Paper 511 审稿报告

## Review setup

- 检测轴：`conference / full-manuscript / ai-ml / standard`
- 评估边界：基于提交的 16 页匿名 PDF；未运行作者代码，也未获得补充材料、数据清单、伦理批件或数据划分文件。
- 中心主张：IIEViT-ROI 通过肺区 ROI 门控、VGG19 多尺度特征和交替 CNN-ViT 交叉注意力，在胸片多分类中实现可解释、快速且具有跨域适应能力的预测。
- 可见证据：3 个公开数据集及其合并集上的单次 80:20 训练/验证实验；VGG19+CNN、IEViT、X-Vision 三个复现基线；110 张本地临床子集的迁移学习；模块消融、混淆矩阵和批量推理延迟。

## Major rejection risks

1. **[Critical，Sec. 3.1] 报告结果不是独立测试结果。** 公开数据只按图像做 80:20 训练/验证划分，验证集同时用于 early stopping 和最终性能报告，且每个结果只有一次训练。这样会把模型选择偏差直接带入 Table 1，无法支持“泛化”“鲁棒”或接近临床可用的结论。应建立患者级、互斥的 train/validation/test 划分；锁定模型后只评估一次测试集，并报告至少 5 个种子的均值、标准差和置信区间。

2. **[Critical，Sec. 3.1] 图像级划分与未去重的合并集有严重泄漏风险。** 医学影像数据常包含同一患者的多张片、重复发布或跨仓库重叠。论文明确写明未做跨数据集重复移除，却把三个来源手工合并后随机按图像划分。这可能让近重复图像或同一患者进入训练和验证两侧。应按患者/检查分组，使用哈希和感知哈希去重，并给出每个源数据集的样本来源、患者数、排重数量及划分清单。

3. **[Critical，Sec. 3.3、Table 2] 临床微调后的“全临床数据测试”不能视为外部验证。** 论文报告 95.56% validation accuracy 后，又在全部 110 张临床图像上报告 96.36%；如果微调使用了其中的训练子集，则“all clinical dataset”包含训练样本。该数值不能证明跨域泛化，且 110 张中 Normal 81、Pneumonia 20、TB 9，类别极不平衡。应采用患者级嵌套划分或交叉验证，并保留完全未参与微调的外部测试中心；不得用含训练样本的全集指标作为泛化证据。

4. **[Critical，Sec. 3.3] 统计检验不能回答模型是否优于基线。** 对混淆矩阵做卡方检验以及 TB-vs-non-TB 的 Fisher 检验，只说明预测与标签不是独立/随机，并不检验 IIEViT-ROI 是否优于 X-Vision，也不能修复样本复用。应对同一独立测试病例做配对比较，例如 McNemar 检验、患者级 bootstrap 的 AUROC/AUPRC/敏感度差异区间，并预先定义主要终点。

5. **[Major，Sec. 3.3] 人体数据伦理信息不足。** 文中只给出临床科室负责人许可、口头同意、匿名化和《赫尔辛基宣言》，没有独立伦理委员会/IRB 名称、审批或豁免编号、口头同意获批依据，也没有说明报告与图像的二次使用范围。对于来自六家机构的人体医学影像，这不足以完成合规审查。应补全伦理审批主体、编号、日期、同意程序和数据治理说明；若处于双盲阶段，可在保密补充材料中提供可核验信息。

6. **[Major，Sec. 2、Sec. 4] ROI 与“可解释性”的核心证据不成立。** U-Net 的训练数据、分割标签、Dice/IoU、失败病例均未报告；注意力图仅作定性展示，没有病灶定位真值、放射科医师评价或 faithfulness 测试。更关键的是，Table 3 中去掉 ROI 后，Lung Disease 与 COVID-19 Radiography 的 accuracy 反而高于完整模型，和“完整模型始终最强”的表述冲突。应单独验证 ROI 分割，报告带置信区间的定位指标，并用 pointing game、删除/插入、病灶遮挡及医师盲评检验解释；同时如实收窄 ROI 的性能主张。

7. **[Major，Sec. 3、Table 1] 基线覆盖与复现公平性不足。** 三个主要基线中两个由作者按论文描述重写，原始划分和训练集不可得；对比中缺少更强且常用的医学影像骨干、现代轻量模型及同规模 CNN/ViT 控制。当前结果最多证明作者实现下的内部比较。应发布精确配置，加入强公开实现，并控制预训练、增强、调参预算、参数量和输入分辨率。

8. **[Major，Sec. 3.1、Table 1] 0.88--1.16 ms 的“部署/实时”结论证据不足。** 该延迟来自 RTX A4000、batch size 16 的吞吐测试，不代表单病例延迟或资源受限设备；文中也未明确把 ROI U-Net、数据传输、预处理和可视化全部计入端到端计时。训练时间反而显著更长，且缺少 FLOPs、显存、功耗和边缘设备数据。应同时报告 batch=1 与 batch=16、warm-up、重复次数、分位数、端到端组件边界，以及目标设备上的测量。

## Technical review

### Scope

胸片分类、可解释 AI 和高效混合网络符合 PRICAI/AI 会议范围。问题重要，低资源场景也有明确工程动机。但论文当前多次使用“clinical applicability”“deployment”等措辞，而证据仍是回顾性验证和极小规模微调，应用定位明显超出验证边界。

### Novelty

ROI 门控 tokenization 与交替 CNN-ViT cross-attention 的组合具有一定工程新意，但各组成部分均较成熟。最接近工作的差异主要靠文字陈述，没有受控对照证明该组合相对普通 mask concatenation、attention rollout 或同参数量混合骨干的独特价值。需要加入机制级替代消融，而不仅是删除模块。

### Validity

- Eq. (2) 固定使用 `0.7x + 0.3x_enhanced`，而后文又称 ROI 为“learnable confidence-aware gating”；固定增强与可学习门控的边界和具体公式不清。
- Cross-attention 的 query/key/value、两个 CNN token 的构造、辅助分类头和残差系数 alpha 未完整定义，难以复现。
- “full cross-attention 每层增加约 0.18 ms 且不提升准确率”没有出现在消融表中。
- 训练超参数只作概述，缺少学习率、权重衰减、各模块差分学习率、类别权重计算和超参数选择过程。

### Data and experiments

- 医疗分类应报告 AUROC/AUPRC、类别级敏感度/特异度、置信区间和校准，而不仅是 accuracy 与 macro-F1。
- 单次运行不能支持 1--2 个百分点差异；没有统计不确定性。
- 合并标签由人工 harmonization，但映射规则、冲突标签处理与来源分布未给出。
- 本地 176 张中排除 66 张、只保留能映射到公开标签的 110 张，可能引入选择偏差；应提供预先定义的纳排标准。
- 需要真正的 leave-one-dataset-out、leave-one-site-out 或不经目标域微调的外部测试，才能支撑 domain shift 主张。

### Clarity

论文的问题链条总体清楚，也主动承认没有独立测试集和临床样本很小，这是优点。但结果段仍使用“confirm”“robust”“validating adaptability”等强词，与承认的证据限制冲突。Table 3 对 ROI 的结果解释尤其需要纠正。

### Compliance

双盲外观基本保持，但正文给出公开 tinyurl，应确认仓库完全匿名且不泄露提交历史。人体数据伦理与同意程序是主要合规风险。最终版本还应通过模板、匿名性、引用和 PDF 检查。

### Advancement

若严格重做患者级外部验证并验证解释模块，该工作可能形成有价值的高效胸片研究系统。按当前证据，优势主要是特定 GPU 上的批量吞吐，准确率常低于 X-Vision，ROI 也并非稳定提升，尚不足以证明显著推进。

## Presentation and first impression

- **Figures/tables：** Fig. 1 信息密度过高，子模块标签和张量尺寸在单栏宽度下过小；Fig. 2 混淆矩阵类名倾斜且字号偏小。Table 1/3 行列拥挤，训练时长、参数和延迟混在主性能表中，扫描效率低。
- **Formatting/notation：** 页眉多处显示 “Title Suppressed Due to Excessive Length”，说明匿名模板中的短标题设置不完整；`Inf.(ms)` 应明确是 per-image batch amortized latency。`Preci.` 等缩写也应在表注定义。
- **Writing：** 存在主谓一致、冠词和标点问题，例如结论中的 “Although,”。部分临床措辞过强，应统一改为 retrospective research / triage-assistance candidate。

## Actionable revision plan

1. 先重建患者级、去重后的 train/validation/test 和独立外部站点测试协议，冻结模型后重跑所有结果。
2. 将临床数据分为微调集和完全独立测试集，删除“test with all clinical dataset”指标；扩大 TB 样本并报告区间。
3. 补齐 IRB/伦理审批、口头同意依据、六中心治理和纳排标准。
4. 用强公开基线、同规模控制、5 个以上种子和配对统计检验重做比较。
5. 单独验证 U-Net 与解释 faithfulness；修正 ROI 消融与文字结论冲突。
6. 在 batch=1、batch=16 和目标低资源硬件上做端到端性能测量，明确计时边界。
7. 简化 Fig. 1、拆分 Table 1、放大类名与图注，并全面收窄临床部署措辞。

## Likely decision posture

按当前提交证据，倾向 **拒稿/完成根本性实验重构后重投**。主要原因不是准确率略低，而是公开集和临床集的评估协议无法提供独立、无泄漏的泛化证据，且解释性与伦理链条尚未闭合。该判断是技术风险评估，不代表程序委员会最终决定。
