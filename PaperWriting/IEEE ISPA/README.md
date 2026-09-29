# IEEE ISPA 2026 投稿资料包

整理日期：2026-09-29（Asia/Shanghai）。本目录针对 **第 24 届 IEEE International Symposium on Parallel and Distributed Processing with Applications（IEEE ISPA 2026）**，不是名称相近的图像/信号处理会议。

## 先看结论

- **投稿截止**：2026-09-30 23:59 AoE（Anywhere on Earth，UTC−12）。换算为北京时间是 **2026-10-01 19:59**。因此在中国大陆提交时不要按 9 月 30 日 23:59 计算。
- **录用通知**：2026-10-30。
- **Paper registration**：2026-11-30。
- **Camera-ready**：2026-11-30。
- **会议**：2026-12-27 至 2026-12-30，吉隆坡，马来西亚。
- **投稿入口**：EDAS，<https://edas.info/N35627>。
- **格式**：IEEE Computer Society Proceedings Format；官方 CFP 没有要求 LNCS，也没有要求双盲。评审是 **single-blind**。
- **篇幅**：CFP 原文写明 full regular paper 最多 8 页免费页，可购买最多 2 页（总上限 10 页）。同一段还写了 “Regular papers or special session papers” 最多 6 页免费页、再加 2 页（总上限 8 页），其中 regular paper 的重复表述存在歧义；普通论文按 8+2 准备，同时在 EDAS 选择稿件类型时核对页面上限。
- **出版**：由 IEEE Computer Society Press 出版；CFP 声明录用论文将提交 IEEE Xplore 和 EI。是否最终收录仍以 IEEE/EI 的出版与检索流程为准。

## 你的稿件适配性

参考文件是 [`sources/pricai2026_submission_reference.pdf`](sources/pricai2026_submission_reference.pdf)，当前 17 页、匿名作者、LLNCS 风格。主题是 TEE、联邦学习、信任建模和恶意更新防御，和 ISPA 的下列方向直接匹配：

- Track 1：Systems and Architectures（edge/cloud、分布式系统）；
- Track 2：Technologies and Tools（并行/分布式计算、可靠性）；
- Track 4：Security and Block-chain（**federated learning**、parallel AI security、edge/cloud security）。

建议把论文定位为“面向边缘联邦学习的可信分布式聚合/安全系统”，突出并行与分布式执行、系统架构和可复现实验。当前 17 页远超免费 8 页，需要压到 8 页以内（或确认付费后最多 10 页）；同时将 `llncs.cls` 改为 `IEEEtran` Computer Society conference 模式，并把匿名作者信息恢复为真实作者。具体压缩和改稿清单见 [`paper_fit_review.md`](paper_fit_review.md)。

## 目录说明

### `sources/`

- `ISPA2026-CFP.pdf`：官网提供的正式 Call for Papers 原件。
- `ISPA2026-CFP.txt`：上述 PDF 的文本抽取，便于搜索。
- `official_ispa2026_page.html`：官网页面快照。
- `overleaf_ieee_compsoc_template.html`：IEEE 官方 Overleaf Computer Society conference 模板页面快照。
- `pricai2026_submission_reference.pdf/.txt`：从原 PRICAI 目录复制的投稿稿件及文本，用于适配检查。

### `templates/`

- `ispa2026_bare_conf_compsoc.tex`：IEEE 官方 Overleaf 模板中的 Computer Society conference 骨架副本。
- `IEEEtran.cls`、`IEEEtran.bst`：模板所需的 IEEEtran 类文件和 IEEE BibTeX 样式。
- `IEEEtran/`：完整 IEEEtran 模板包（含 `bare_conf_compsoc.tex`、说明文档和测试文件）。
- `IEEEtran.zip`：完整模板包压缩文件。
- 根目录 `template_notes.md`：ISPA 规则与模板使用要点。

### 其他

- [`submission_checklist.md`](submission_checklist.md)：提交前逐项检查表。
- [`paper_fit_review.md`](paper_fit_review.md)：针对当前稿件的适配评估与压缩方案。
- [`conference_info.md`](conference_info.md)：会议、委员会、四个 track、日期、投稿/出版规则的完整整理。
- [`source_urls.md`](source_urls.md)：来源、用途和核验日期。

## 已生成的第一版草稿

- [`ispa2026_draft.tex`](ispa2026_draft.tex)：由 `PRICAI 2026/pricai2026_submission.tex` 转换而来，使用 `IEEEtran` Computer Society conference 格式，暂未压缩正文。
- [`ispa2026_draft.pdf`](ispa2026_draft.pdf)：已成功编译，当前 **11 页**（US Letter，双栏）。这是保留完整内容、把图表改为跨双栏浮动后的初版页数，后续还需要压缩到会议允许范围。
- `figures/`：编译所需的 11 个 PDF 图，来自 `PaperWriting/` 下的原图文件。
- `ispa2026_draft.log`：编译日志。当前仅有少量公式的 overfull/underfull 排版提示，没有编译错误；正式压缩时需进一步处理。

## 需要特别核对的事项

1. CFP 同时出现“regular 8 页”和“regular or special session 6 页”的文字。普通稿先按 8 页免费、最多 10 页准备；若 EDAS 的具体 track 页面给出不同限制，以 EDAS 和会议主席最新通知为准。
2. 官网公开页面没有列出注册费、是否必须现场报告、每篇论文的作者注册政策或 PDF eXpress conference ID。录用后要在 EDAS/会议通知中确认，不能从往届 ISPA 规则推断本届费用。
3. 截至整理日期，官网给出的截止日期仍是 2026-09-30 AoE；如果页面临近截止时间发生更新，以官网/EDAS 的时间戳为准并保留提交成功页面。
