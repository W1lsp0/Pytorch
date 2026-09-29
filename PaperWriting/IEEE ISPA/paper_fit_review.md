# 当前稿件与 IEEE ISPA 2026 的适配评估

参考稿：`sources/pricai2026_submission_reference.pdf`（从 `PaperWriting/PRICAI 2026/pricai2026_submission.pdf` 复制，17 页）。

## 匹配度

当前题目为 “TTFL: Trust-Flow-Driven Federated Learning with TEE-Anchored Admission”。论文研究联邦学习中的 TEE 可信准入、恶意更新/后门防御、跨轮信任状态和分层聚合。ISPA 2026 CFP 明列 “Federated learning”“Security in parallel AI systems”“Blockchain in edge and cloud computing”，官网还强调 distributed/parallel、edge、cloud 和 large-scale systems，因此主题匹配度高。

建议在摘要、引言和贡献中增加以下系统视角：

- TEE 证明、客户端更新审计和跨轮状态如何在分布式训练系统的时序中衔接；
- Flower/PyTorch、Intel/AMD TEE 硬件配置和客户端并发如何体现并行/边缘部署价值；
- 运行时开销、通信开销、吞吐、延迟、可扩展性和故障恢复，而不仅是精度/攻击成功率；
- 对“安全保证”的边界：30% 恶意客户端、指定攻击行为和 Non-IID 设置不能推导出无条件安全结论。

## 必须改的格式问题

1. **页数**：17 页 → 目标 8 页以内；确认 EDAS 后再决定是否使用付费的第 9–10 页。
2. **模板**：LLNCS 单栏/章节风格 → IEEE Computer Society `IEEEtran` 双栏。
3. **匿名性**：当前 PDF 为 “Anonymous Author(s)”；ISPA CFP 明确 single-blind，准备投稿稿时恢复作者姓名、单位和联系信息。
4. **引用与图表**：按 IEEEtran/BibTeX 规范重排引用、图题、表题和公式，所有对象都占页数。
5. **元数据**：EDAS 标题、摘要、作者顺序必须和 PDF 一致；不要把 PRICAI 的投稿信息直接沿用到 ISPA。

## 8 页压缩建议

优先保留方法定义、威胁模型、实验协议和核心结果，压缩背景叙述与重复消融说明：

| 部分 | 建议目标 |
|---|---:|
| 标题、摘要、关键词 | 约 0.3 页 |
| 引言与贡献 | 0.6–0.8 页 |
| 背景/相关工作 | 0.6–0.8 页 |
| 系统模型与 Trust Flow 方法 | 2.0–2.3 页 |
| 实验设置与主要结果 | 2.2–2.6 页 |
| 消融、边界压力测试、局限性 | 0.8–1.0 页 |
| 结论与参考文献 | 1.0–1.3 页 |

压缩时不要删除：初始化策略、Kalman 递推、Beta/EMA 更新、逐层剪裁/重归一化规则、攻击定义和统计口径。可以把重复的硬件细节、完整参数表和次要结果移到紧凑表格，删掉与方法无关的长篇背景。

## 建议的新结构

1. Introduction（问题、系统场景、贡献）
2. System and Threat Model（TEE、客户端、攻击者能力、假设）
3. Trust-Flow Aggregation（准入证据、Kalman、Beta/EMA、分层聚合）
4. Evaluation（平台、数据、Non-IID、攻击、基线和指标）
5. Results and Ablations（主结果、消融、压力测试、开销）
6. Limitations and Conclusion

这个结构比当前 LNCS 版本更直接地对应 ISPA 的 systems/security 读者。结果部分至少应同时报告 clean accuracy、targeted ASR、loss/utility、误禁/漏检以及运行或通信开销。

## 投稿定位建议

- **首选 track**：Track 4 — Security and Block-chain，关键词选择 federated learning、security in parallel AI systems、edge/cloud security。
- **可补充 track**：Track 1 — Systems and Architectures；Track 2 — Technologies and Tools。
- 标题可保留 TTFL，但摘要第一句应直接说明这是面向 edge/distributed FL 的可信聚合系统，避免看起来只是通用安全算法。

