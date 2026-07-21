# PRICAI 2026 Paper 614 审稿报告（PRICAI long-paper 校准版）

## Review setup

- 检测轴：`PRICAI conference / long paper / full-manuscript / ai-ml / standard`
- 会议校准：PRICAI 接受增量但完整的多模态学习方法；三数据集、合理基线、组件消融和鲁棒性分析通常比顶会式理论新颖性更重要。
- 评估边界：基于提交的 16 页匿名 PDF；未运行代码，也未获得每项实验的逐种子结果或补充实现。
- 中心主张：DUKAN 在 KAN-MCP 上加入共享/特定子空间正则与基于 VIB posterior scale 的逐样本模态 gate，以提高多模态情感分析性能和污染鲁棒性。
- 可见证据：MOSI、MOSEI、CH-SIMS v2 三个基准；与多种文献方法及 KAN-MCP 对比；组件、gate、超参数、feature-dropout、效率和表示可视化分析。

## 主要审稿问题

1. **[Major，Sec. 3.4、Sec. 5.6] posterior standard deviation 被过度解释为 aleatoric uncertainty。** VIB 的 latent posterior scale 由任务损失、KL 和重参数化共同学习，不自动等于输入模态噪声。stop-gradient 也只切断 gate 路径，不能让 sigma 成为“pure uncertainty”。建议将术语改为 `posterior dispersion/reliability proxy`，并增加它与单模态预测误差或 corruption 强度的相关分析。

2. **[Minor，Fig. 2] gate 与 uncertainty 的强负相关主要由公式决定。** `g=softmax(-u/T)` 天然产生负相关，因此 `rho=-0.95` 不能作为 uncertainty 正确性的独立证据。保留该图可以解释机制，但应删除“验证可靠性”的表述，并用 error/corruption correlation 作为真正验证。

3. **[Major，Table 1/2] SOTA 表混合了作者复现和不同论文报告值。** 只有 KAN-MCP 明确标注复现，其他方法可能使用不同文本骨干、特征或二分类协议。PRICAI 不要求全部重跑，但至少应统一复现最接近的 KAN-MCP 和一个强分解/融合基线，或者在表注中明确 `reported from original papers`，避免直接声称严格 SOTA。

4. **[Major，Table 1--6] 关键提升缺少运行波动。** 文中称 headline results 为五种子均值，但表格没有标准差或显著性。MOSI 上 0.4--0.8 点差异可能处于随机波动内。建议只对 proposed、KAN-MCP 和最强近邻报告 mean±std；无需为所有历史基线补统计。

5. **[Major，Sec. 5.4] feature-dropout 结果没有直接证明 gate 识别了坏模态。** full model 在 clean setting 已优于 w/o gate，污染后的差距可能只是基础优势。应报告 corruption 前后 posterior dispersion 和 gate weight 的变化，以及相对 clean performance drop；一个 paired 分析即可，不必构建大规模鲁棒基准。

6. **[Major，Sec. 3.3] zero cross-correlation 只能证明线性去相关，不能证明独立 disentanglement。** t-SNE/silhouette 也不是独立性证据。建议把 `statistically independent` 改为 `decorrelated`，保留 shared/specific 的工程解释；HSIC/MI probe 属于增强项而非必须项。

7. **[Major，Sec. 3.5] KAN 的“可解释性”主张没有实际展示 edge splines。** 当前 Fig. 2 是 gate、Fig. 3 是 t-SNE，并未解释 KAN 决策。对 PRICAI，可选择补 1--2 个 edge-function 或局部案例；若版面有限，删除“interpretable backbone”中心主张，不影响主要性能贡献。

8. **[Minor，Sec. 4] CH-SIMS v2 配置不足。** 应补充 split、中文文本 backbone、声视觉特征和主要超参数。无需在 CH-SIMS 上重复所有消融，但必须让主结果可复现。

9. **[Minor，Sec. 3.6] MMPareto 的 rescale 步骤未完整定义。** 因该模块继承自 KAN-MCP，可引用原算法并明确本稿未修改部分，同时给出使用的关键参数。

## Technical review

### Scope

多模态情感分析、信息瓶颈、可靠性加权和 KAN 均符合 PRICAI 范围。三个数据集覆盖英语和中文，应用与方法平衡较好。

### Novelty

InfoNCE、cross-correlation penalty 和 uncertainty-inspired gate 都不是新原语，但把 IB posterior scale 复用于轻量 gate，并与 KAN-MCP 结合，具有合理的增量新意。对 PRICAI 而言，这类清晰组合加完整实验可以达到 long-paper 门槛。

### Validity

主要机制在公式层面较完整。需要注意不同模态 posterior scale 未必天然可比、shared/specific 各 2 维非常小、MOSI batch size 8 对 InfoNCE negatives 有限制。上述问题可通过讨论和轻量敏感性分析处理，不构成当前致命缺陷。

### Data and experiments

三数据集、组件消融、gate 变体、超参数、鲁棒性和效率覆盖已经符合 PRICAI 常见完整度。最需要补的是主结果波动和统一的最近邻对比，而不是继续增加更多数据集或工业实验。

### Clarity

方法组织和符号总体清楚。需将 `aleatoric uncertainty`、`pure uncertainty`、`statistical independence`、`genuine reweighting` 等强措辞改成与证据匹配的描述。

### Compliance

匿名性未见明显问题。正文和参考文献有红/绿 hyperlink 边框，应在最终 PDF 中隐藏。代码承诺未来公开可以接受，但匿名配置或伪代码应足够完整。

### Advancement

相对 KAN-MCP 的改进幅度不大，但在三个数据集上方向较一致，并有组件和鲁棒性分析。按 PRICAI 标准，这是可讨论的增量推进；是否接收主要取决于审稿人是否认可 posterior dispersion gate 的合理性和比较公平性。

## Presentation and first impression

- **Figures/tables：** Fig. 1 标签偏小；Fig. 2(b) 容易把公式必然关系包装成经验发现；Fig. 3 清楚但只能作为定性辅助。Table 1/2 信息密集。
- **Formatting/notation：** 引用和交叉引用有彩色方框；`sd/pd` 与 `d_s/d_p` 应统一。Table 7 应说明 latency 是否包含声视觉特征提取。
- **Writing：** 英文成熟，主要需要收窄 uncertainty、independence 和 interpretability 的措辞。

## Actionable revision plan

1. 将 sigma 重命名为 posterior-dispersion reliability proxy，并验证其与误差或污染强度的关系。
2. 为 proposed、KAN-MCP 和一个最强近邻补 mean±std，明确其他表格值来自原论文。
3. 在 robustness 表中增加 gate/dispersion shift 或相对性能下降。
4. 把 independence 改为 decorrelation；补一个 KAN edge 案例或删除可解释性强主张。
5. 补齐 CH-SIMS 配置和 MMPareto 引用/参数。
6. 修复彩色链接、字号和表注。

## Likely decision posture

按 PRICAI 2026 long-paper 标准，当前倾向 **边缘接收至弱接收**。论文的增量创新、三数据集结果和消融覆盖基本匹配会议；主要问题集中在术语过度解释、统计波动和比较协议，而非核心实验无效。若作者在 camera-ready/rebuttal 中收窄 uncertainty/independence/interpretability 主张并补最小统计证据，接收判断较合理。该判断不代表程序委员会最终决定。

## Final PRICAI / EasyChair Review

### Overall evaluation

weak accept

### Reviewer confidence

medium

### Review text for authors

This paper proposes DUKAN, an extension of KAN-MCP for multimodal sentiment analysis that combines shared/specific subspace regularization with a lightweight modality gate based on VIB posterior scale. The paper is relevant to PRICAI, and I found the submission comparatively complete. It evaluates on MOSI, MOSEI, and CH-SIMS v2, compares against several prior methods and KAN-MCP, and includes component ablations, gate variants, hyperparameter analysis, feature-dropout robustness, efficiency measurements, and representation visualizations. The writing is generally clear, and the method is easy to follow.

My overall recommendation is weak accept, mainly because the paper offers a coherent incremental contribution with a reasonably broad empirical evaluation. That said, several claims should be narrowed or better supported. The most important issue is the interpretation of posterior standard deviation as aleatoric uncertainty. In a VIB-style latent posterior, the scale is learned through task loss, KL regularization, and reparameterization; it does not automatically correspond to input noise or irreducible modality uncertainty. The stop-gradient design prevents a particular feedback path but does not make the scale a pure uncertainty estimate. I recommend renaming it as a posterior-dispersion or reliability proxy and adding a direct check against unimodal error or corruption strength.

Relatedly, the strong negative correlation between gate weights and uncertainty in Fig. 2 is partly implied by the formula `g = softmax(-u/T)`, so it should not be presented as independent evidence that the uncertainty estimate is valid. The feature-dropout experiment is useful, but it would be more convincing to report how dispersion and gate weights change before and after corruption, and to compare relative performance drops against the clean setting.

The empirical comparison also needs some clarification. The SOTA tables appear to mix values reproduced by the authors with values reported in prior papers, possibly under different features or protocols. PRICAI does not require rerunning every historical baseline, but the paper should clearly mark which results are reproduced and should at least report mean+/-std for DUKAN, KAN-MCP, and the strongest nearest baseline. Some gains, especially on MOSI, may be within run-to-run variation without this information.

Finally, the paper should avoid overstating independence and interpretability. Zero cross-correlation supports decorrelation, not statistical independence, and the current figures do not actually show KAN edge-function interpretability. These are fixable presentation and evidence issues rather than fatal flaws. With more conservative wording, minimal statistical evidence, and clearer comparison notes, the paper would make a solid PRICAI contribution.

### Confidential remarks for the PC

I lean weak accept because the empirical package is substantially stronger than the other assigned papers, and the main issues are over-interpretation and reporting clarity rather than invalid core experiments. Acceptance would be more comfortable if the authors can provide variance for the main comparisons and soften the uncertainty/independence/interpretability claims.
