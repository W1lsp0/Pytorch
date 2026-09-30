# IEEE Computer Society 模板使用说明

ISPA 2026 CFP 指定 **IEEE Computer Society Proceedings Format**。本目录提供的 `ispa2026_bare_conf_compsoc.tex` 是 IEEE 官方 Overleaf 模板页面对应的骨架，类文件为 IEEEtran 1.8b 系列；`IEEEtran/` 中保留了完整模板包和 HOWTO 文档。

## LaTeX 起点

```latex
\documentclass[conference,compsoc]{IEEEtran}
```

Computer Society 模板对引用格式、图表标题和字体有自己的处理，先使用模板默认设置，再逐项替换正文。不要自行修改页边距、栏宽、字号、行距或 `IEEEtran.cls` 的内部参数。最终 PDF 必须是双栏会议论文格式，正文、图、表、公式和参考文献都计入页数。

## 使用步骤

1. 复制 `ispa2026_bare_conf_compsoc.tex`，将标题、作者、单位、摘要、关键词和正文替换为论文内容。
2. 将当前稿件中的 `llncs.cls`、Springer 标题页和匿名作者设置移除；ISPA 的 CFP 是 single-blind，作者信息按 EDAS 元数据填写并放入稿件。
3. 使用 `IEEEtran.bst` 或模板指定的 IEEE 参考文献样式；检查 DOI、作者、卷期和页码。
4. 编译后用 `pdfinfo` 检查页数和页面尺寸，目视检查双栏溢出、图中文字、表格和参考文献。
5. 以 PDF 上传 EDAS。若 EDAS 之后提供 PDF eXpress 检查入口，再按会议给出的 conference ID 执行检查；不要使用其他会议的 ID。

上级目录此前的 `ispa2026_draft.tex` 已经按上述流程做了第一轮转换并成功编译为 `ispa2026_draft.pdf`。该版本保留了 PRICAI 原稿的全部正文、公式、表格和图，当前为 11 页；其中跨双栏图表使用 `figure*`/`table*`，尚未进行投稿页数压缩。

## Word 用户

从 [IEEE Template Selector](https://template-selector.ieee.org/) 选择 Conference → Computer Society/Proceedings 对应的 Word 模板。不要使用普通期刊模板或 LNCS 模板。提交前删除模板中的示例说明文字。

## 页数策略

普通论文建议先把正文压到 8 页以内；第 9–10 页只有在 EDAS 明确允许并且注册后可购买额外页时才使用。图和参考文献也计入页数，不能通过缩小字体或改边距规避限制。
