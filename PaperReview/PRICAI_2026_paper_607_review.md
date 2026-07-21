# PRICAI 2026 Paper 607 审稿报告（PRICAI long-paper 校准版）

## Review setup

- 检测轴：`PRICAI conference / long paper / full-manuscript / ai-ml / standard`
- 会议校准：PRICAI 接受探索性 AI 应用和透明的负面/诊断结果；但 16 页 long paper 仍应证明所提指标比简单基线更有信息。若只做可行性展示，内容更接近 short paper。
- 评估边界：基于提交的 16 页 PDF；未获得事件数据、代码、完整球员排名或分析师标注。
- 中心主张：使用 Transformer 对完整射门回合拟合提供方 xG，再聚合 final-shot attention，形成事件级和球员级贡献分数及可视化。
- 可见证据：单赛季 306 场、8,441 个射门回合、五个种子、特征消融、attention entropy、排名稳定性、uniform control 和定性案例。

## 主要审稿问题

1. **[Major，Sec. 3.2] 主任务包含作者已明确承认的 target-feature leakage。** final shot token 含有可能直接决定 provider xG 的位置、类型或结果，因此模型更像重构现有 xG，而不是学习此前 buildup 的价值。透明承认这一点值得肯定，但对于 long paper，至少应加入一个 `preceding events only` 设置并把它作为主要或并列实验；不必构建完整新 xG 系统。

2. **[Major，Sec. 3.4] attention sum 不能直接等同于球员边际贡献。** 当前分数始终非负、每个序列总量固定为 1，并随球员事件次数增长，也可能包含最终射手。建议把术语统一为 `attention-based involvement/reliance score`。如果继续使用 contribution，需要增加一个简单的 leave-one-event-out 或 occlusion 对照，证明高 attention 事件确实更影响预测。

3. **[Major，Table 2] uniform attention 与 learned attention 的排名几乎相同。** uniform control 的 Spearman 为 0.9970，说明排名可能主要由参与次数、序列长度和 xG 权重驱动。论文目前将 top-10 变化解释为 learned attention 有效，但没有展示相对 involvement count 的增量价值。应直接比较 count、uniform 和 learned attention，并报告控制 sequence count 后的相关或排名变化。

4. **[Major，Sec. 3.5] 缺少独立测试集和最小预测基线。** validation 用于 early stopping 后又报告最终 MSE、排名和案例，存在选择偏差。PRICAI 不要求大规模跨联赛实验，但应保留一个 match-level test split，并加入 mean predictor、线性/GBDT aggregated features 或 GRU 中至少一个简单基线。

5. **[Major，Sec. 4.3] 外部效度主要依赖少数成功案例。** top scorer、Player of the Season 等例子有直观吸引力，但 `xG-weighted contribution` 本身乘了 provider xG，与攻击数据自然相关。建议对全部达到最小参与阈值的球员报告与 minutes、G+A、xG+xA 或一种行动价值指标的相关，并控制出场次数。无需为 PRICAI 强制开展大规模专家盲评。

6. **[Major，Sec. 3.4] attention 的 faithfulness 仍未测试。** 平均最后两层/多头会忽略 residual 和 FFN 路径，entropy 与跨消融稳定性也不等于解释忠实度。一个基础的 top-attention deletion 与 random deletion 对比已经足以显著增强稿件。

7. **[Major，Sec. 3.1] 数据构造细节不足。** 需要明确供应商/数据版本、possession 定义、事件 outcome、射门字段、缺失值、坐标方向和被截断序列比例。单赛季单联赛对 PRICAI 探索性应用可以接受，但结论必须限定在该赛季和联赛。

8. **[Critical，Acknowledgements] 双盲匿名性被致谢直接破坏。** 稿件列出 Adam Mickiewicz University 和 KKS Lech Poznan，可能触发程序性问题。审稿版必须匿名化；这项修改简单但优先级最高。

## Technical review

### Scope

体育事件序列、可解释 AI 和决策支持符合 PRICAI 应用范围。文章对 attention 非因果和 leakage 风险的讨论诚实、清楚，具有一定方法论价值。

### Novelty

标准 Transformer 加 final-token attention aggregation 的算法创新有限，但把可解释性审计、排名稳定性和足球应用结合起来，作为 PRICAI 应用研究具有一定新意。long paper 需要再证明 learned attention 超过简单参与统计；否则更适合作为 short paper。

### Validity

`no_player` 的 validation MSE 优于完整模型，说明身份信息可能造成过拟合；该结果应正面讨论。`xG-weighted contribution` 混合外部 xG 与本模型 attention，需要清楚分解，不应全部归功于 Transformer。

### Data and experiments

数据规模和五次运行足以支持探索性研究，主要不足是没有独立 test 和简单基线。跨赛季/跨联赛验证属于增强项，不是 PRICAI 当前稿件的必要条件。建议增加最小参与阈值和 bootstrap 区间，但无需构建完整职业球探验证体系。

### Clarity

问题、边界、公式和限制写得较清楚，是本文优势。Sec. 4 中的 `successfully identify and value` 应改成 `highlight potentially influential involvement`，与结论的保守定位一致。

### Compliance

匿名致谢是明确问题。还应说明事件数据许可。正文和参考文献的彩色 hyperlink 边框需要隐藏。

### Advancement

本文更像透明、可复查的可行性研究，而不是已验证的球员评级系统。对于 PRICAI，若增加无泄漏设置、简单基线和 attention 增量证据，可以形成可接受的应用贡献。

## Presentation and first impression

- **Figures/tables：** Fig. 2 热图字体和分辨率偏低；Fig. 3 案例直观但标签小。Fig. 1 的高度线性关系应明确解释为参与量/xG 混杂证据。
- **Formatting/notation：** Table 3 的 `Total`、`Mean`、`xG-wtd.` 应定义单位；彩色链接边框影响 LNAI 成稿观感。
- **Writing：** 英文整体清楚，免责声明略重复，可压缩后腾出版面给无泄漏实验和基线。

## Actionable revision plan

1. 立即匿名化致谢和合作机构信息。
2. 增加 `preceding events only` 主实验和独立 match-level test split。
3. 加入 count/uniform 及一个简单预测基线，量化 learned attention 的增量价值。
4. 将 `contribution` 收窄为 `attention-based involvement`，或增加一个 occlusion faithfulness 测试。
5. 对满足参与阈值的全部球员报告一种整体外部相关，而不是只列成功案例。
6. 补全数据构造，修复热图、字号和 hyperlink 边框。

## Likely decision posture

按 PRICAI 2026 long-paper 标准，当前倾向 **弱拒稿**，而不是明确拒稿。稿件的透明边界意识和应用价值值得肯定，但主任务 leakage、uniform control 几乎复现排名、缺少独立 test，使 16 页 long paper 的核心证据不足。若改投 short paper，或补上无泄漏设置、简单基线和匿名修复，接收可能性会明显提高。该判断不代表程序委员会最终决定。

## Final PRICAI / EasyChair Review

### Overall evaluation

weak reject

### Reviewer confidence

medium

### Review text for authors

This paper studies the use of Transformer attention to quantify player involvement in football event sequences. The topic is within the PRICAI application scope, and the paper has several strengths. The problem is clearly motivated, the authors are unusually transparent about the limitations of attention-based explanations, and the analysis includes seed variation, entropy, ranking stability, a uniform-attention control, and qualitative examples. The paper is readable and could be valuable as an exploratory study of how sequence models behave in sports analytics.

My main concern is that the current evidence is not yet strong enough for a 16-page long paper. The prediction target is provider xG for a shot possession, but the final shot token appears to contain information such as shot location/type/outcome that may largely determine the provider xG. The authors acknowledge this target-feature leakage, which is good practice, but the main experiment still evaluates a task that is closer to reconstructing an existing xG model than measuring the value of preceding buildup events. A `preceding events only` setting should be added and treated as a main or at least parallel experiment.

A second major issue is that attention mass is interpreted too strongly as player contribution. The proposed score is always non-negative, sums over event attention, increases with event involvement, and may include the final shooter. This makes it closer to an attention-based involvement or reliance score than a marginal contribution measure. This concern is reinforced by the uniform attention control: a Spearman correlation of 0.9970 between uniform and learned attention rankings suggests that the ranking may be driven mostly by participation counts, sequence length, and xG weighting rather than learned attention. The authors should compare learned attention directly with count/uniform baselines and report the incremental value after controlling for involvement.

The paper also lacks a clean final test protocol and simple prediction baselines. Validation is used for early stopping and then for final MSE/ranking/case analysis, which can introduce selection bias. A held-out match-level test split and at least one simple baseline such as a mean predictor, aggregated-feature linear/GBDT model, or GRU would substantially improve the validity of the claims. External validity currently relies on selected successful examples; a correlation over all players above a participation threshold would be more convincing.

Finally, the acknowledgements reveal institutional/team information, which appears to violate double-blind review. This should be fixed immediately. Overall, I weakly recommend rejection in the current form, but I see a plausible path to acceptance as a shorter paper or as a revised long paper with an anonymous version, a leakage-free task, simple baselines, and more conservative terminology around contribution.

### Confidential remarks for the PC

Please note the apparent double-blind violation in the acknowledgements. The scientific weaknesses are mostly fixable, and the paper is more borderline than a clear reject if the anonymity issue is handled and the authors can add a leakage-free experiment.
