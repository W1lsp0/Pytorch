# PRICAI 2026 Paper 607 审稿报告

## Review setup

- 检测轴：`conference / full-manuscript / ai-ml / standard`
- 评估边界：基于提交的 16 页 PDF；未获得原始事件数据、代码、补充排名或足球分析师标注。
- 中心主张：用 Transformer 预测完整射门回合的提供方 xG，并聚合最终射门 token 对此前事件的 attention，以构造可解释的事件级和球员级进攻贡献分数。
- 可见证据：2025/2026 波兰 Ekstraklasa 306 场、8,441 个射门回合；match-level 的训练/验证划分；五个种子；特征消融、attention entropy、排名稳定性、uniform attention 控制和定性案例。

## Major rejection risks

1. **[Critical，Sec. 3.2] 核心代理任务包含作者已承认的目标泄漏，因而不能验证“球员贡献”。** 输入包含最终射门 token、位置、结果等可能直接决定提供方 xG 的信息，模型很可能重构提供方 xG，而不是学习此前 buildup 对机会质量的贡献。承认此限制是诚实的，但不能把致命有效性问题转化为已解决问题。至少应把主实验改为 pre-shot、masked-shot 和 full-shot 三个预注册设置，并以完全无最终射门信息的设置作为核心结论依据。

2. **[Critical，Sec. 3.4] attention mass 不是边际贡献，当前分数定义缺乏效度。** `Cp(S)` 只是属于球员 p 的 token attention 之和，永远非负、每个序列总和固定为 1，并随事件次数和 tokenization 改变。它不能表达一次动作降低机会质量，也不等价于删除该球员/动作后的 xG 变化。最终射手也被包含在聚合中。应与 action-value 的反事实定义对齐，使用遮挡、leave-one-action-out、Integrated Gradients/SHAP 或状态价值增量，并检验与 VAEP/xT/OBV 的一致和互补部分。

3. **[Major，Sec. 3.5、Sec. 5] 缺少任何强预测或归因基线。** 论文只比较特征删除和 uniform attention，自身也承认没有 gradient boosting、RNN、occlusion、IG、SHAP、VAEP/xT/OBV。对会议完整论文而言，这意味着无法判断 Transformer 是否必要、attention 是否比简单参与次数更有信息、以及新指标是否优于现有行动价值方法。未来工作列表中的这些基线应成为当前主实验。

4. **[Major，Table 2] uniform control 与 learned attention 得到几乎相同的全局排名，实际削弱而非支持核心方法。** uniform attention 的 Spearman 为 0.9970，Jaccard@10 为 0.8545；各消融 Spearman 也都在 0.995 以上。这表明排名可能主要由参与频率、序列长度和 xG 权重驱动，而不是学习到的 attention 结构。论文把 top-10 变化解释为 learned attention 有用，但没有检验相对 involvement count 的增量解释力。应做残差化、分层匹配和 permutation test，并报告排名相对简单计数基线的增益。

5. **[Major，Sec. 3.5、Table 1] 没有独立测试集。** validation set 用于 early stopping、选择最低 MSE epoch，并用于最终 MSE、entropy、排名和案例分析。五个随机种子不能消除这种模型选择偏差。应增加未参与选择的 test matches；更合理的是按时间训练、后续比赛测试，并在另一赛季或联赛外部验证。

6. **[Major，Sec. 4.3] 排名的“外部验证”是选择性轶事且存在循环。** 论文只举 top scorer、Player of the Season 和 assist leader 等少数成功案例，没有对全部球员计算与 G+A、minutes、xG+xA、VAEP 等指标的相关、增量效度或预测效度。`xG-weighted contribution` 又直接乘以提供方 xG，因此它与 xG/进球表现相关并不意外。应预先定义外部标准，覆盖所有合格球员，控制出场时间、位置、球队实力和射门回合数量，并报告 bootstrap 区间。

7. **[Major，Sec. 3.4] attention extraction 不足以支持模型解释。** 只平均最后两层和多头的 final-token attention，忽略 residual path、FFN 和跨层信息传播；不同 attention 分布可产生相同输出。attention entropy 与跨消融排名稳定性不是 faithfulness。应加入 attention rollout、梯度/遮挡 faithfulness、attention randomization 和 model parameter randomization tests。

8. **[Major，Sec. 3.1] 数据与特征构造不够可复现。** “event structures consistent with StatsBomb”不能确定数据供应商、许可、比赛覆盖、possession 规则、事件 outcome 枚举、射门特征、缺失值和坐标方向。长序列截断为最近 20 个事件可能系统性忽略早期组织者，也没有报告被截断比例。应给出数据来源、版本、构造伪代码、特征字典和描述统计，并公开可复现脚本。

9. **[Critical，末页 Acknowledgements] 双盲匿名性被直接破坏。** 稿件明确写出研究合作方 “Adam Mickiewicz University in Poznan” 和 “KKS Lech Poznan”。在匿名投稿中，这足以显著缩小作者身份范围，可能触发程序性拒稿。审稿版应删除或匿名化致谢、机构、项目和可追踪合作信息。

## Technical review

### Scope

体育事件序列建模、可解释 AI 和决策支持符合 AI 会议应用范围。文章把工作明确定位为 exploratory case study，边界意识优于常见的 attention-as-explanation 论文。但完整研究轨的证据门槛仍要求无泄漏任务、强基线和外部效度；“探索性”不能替代这些核心验证。

### Novelty

从 final-shot attention 聚合球员分数的想法直观，但技术上较轻量：标准 Transformer 加简单 attention sum，再乘 xG。与 attention-based event valuation、sequence attribution 和现有 action-value 的差异主要是应用组合，尚未证明方法层面的显著新颖性。需要明确最近邻方法表，并展示新分数捕获了现有指标没有捕获的、可验证的信息。

### Validity

- baseline 中 `no_player` 的 validation MSE 反而低于完整模型，说明 player identity 对预测无益或造成过拟合；论文却用其造成的排名变化讨论身份的重要性，这更可能是指标定义的结构效应。
- 用 source xG `yi` 而不是模型预测 `yhat_i` 加权 attention，使最终排名混合了外部模型的价值判断和本模型 attention；贡献来源应明确分解。
- 排名跨种子的计算方式不清：是否每个消融种子和同编号 baseline 配对，缺失球员如何处理，排名 ties 如何处理。
- MSE 没有与常数均值、仅射门位置模型或提供方 xG 复制基线比较，因此 0.0123 缺乏可解释尺度。

### Data and experiments

- 单赛季单联赛不足以评估转会、教练变化、赛季节奏和联赛风格下的稳定性。
- 应按 position、minutes 和 team possession 分层，防止前锋和强队球员天然拥有更多射门回合。
- Table 3 没有 minimum involvement threshold，也没有任何不确定性区间，尽管正文正确指出此问题。
- 需要检验不同 max sequence length、不同 attention 层/头聚合、仅 pre-shot token、是否含 shooter 等敏感性。
- 应报告目标 xG 分布、序列长度分布、球员参与次数长尾和被截断比例。

### Clarity

文章对 target-feature relationship、因果边界和局限的表述非常清楚，方法定义也相对易懂，这是稿件最强部分。但正文仍在 Sec. 4.3 使用“successfully identify and value”等强表述，与后文“hypothesis-generating signal”不一致。全文应采用后者的保守口径。

### Compliance

匿名致谢是明确合规风险。参考文献中的 URL 以青色边框显示，正文交叉引用出现红/绿框，影响成稿观感；应配置 `hyperref` 隐藏打印边框。还应说明事件数据的使用许可和可共享范围。

### Advancement

论文对 attention 解释风险的透明讨论有教育价值，但当前实证结果主要说明“可以生成一个排名”，没有证明该排名有效、忠实或优于简单统计。按现有版本，技术推进不足以支撑完整会议论文。

## Presentation and first impression

- **Figures/tables：** Fig. 1 的散点关系高度近线性，恰好显示分数受总 xG/参与量支配，却未量化该混杂。Fig. 2 热图分辨率和字体偏低，颜色含义与单位不够清楚。Fig. 3 单案例路径较清晰，但文本标签小，且不能作为总体效度证据。
- **Formatting/notation：** Table 3 的 `Total`、`Mean`、`xG-wtd.` 单位和归一化方式应在表注中完整定义。彩色 hyperlink 边框在正文和参考文献中大量出现，不符合干净的出版版式。
- **Writing：** 英文整体清楚、克制，但 16 页中局限讨论占比很高，反映核心验证尚处于研究设计阶段。可压缩重复免责声明，把版面用于真正的对照实验。

## Actionable revision plan

1. 删除/匿名化致谢和所有可追踪合作信息，先消除双盲违规。
2. 以 pre-shot 无泄漏任务为主，full-shot 仅作为诊断；建立独立、时间后移的测试集。
3. 加入 mean/linear/GBDT/RNN/Transformer 预测基线，以及 count/uniform/occlusion/IG/VAEP/xT/OBV 归因基线。
4. 重新定义或验证贡献：允许正负边际影响，控制事件次数、出场时间、位置和球队强度。
5. 用 faithfulness、randomization、反事实删除和足球分析师盲评验证解释。
6. 对全部符合阈值的球员报告外部效度、bootstrap 区间和跨赛季/跨联赛稳定性。
7. 公布数据构造与特征细节，修复图表字号、热图单位和 hyperlink 边框。

## Likely decision posture

按当前版本，倾向 **拒稿**。作者准确识别了目标泄漏、attention 非因果和弱基线，但这些正是核心结论尚未成立的原因；此外匿名致谢可能单独触发程序性问题。若完成无泄漏任务、强基线和外部效度验证，工作可形成更扎实的后续投稿。该判断不代表程序委员会最终决定。
