# Submission 数据来源与复现

当前稿件只有 `ispa2026_submission.tex` 和 `ispa2026_submission.pdf` 两个入口，文献库为 `ispa2026_references.bib`。不另存编号稿或图件对照册。

## 文件用途

- `figures/`：当前稿件使用的11个图像文件及三张逻辑图的imagegen提示词。
- `protocol/`：构造输入下的控制器、固定配置、验证与绘图脚本、事件CSV和测试结论。
- `local_evidence/`、`extract_local_evidence.py`：已有局部Flwr运行的只读提取材料，不代表作者完整实验。
- `old/ispa2026_submission.tex/.pdf`：作者最初提供的ISPA底稿，作为原始来源保留；不是当前投稿入口。
- `修改.md`、`修改1.md`、`修改2.md`、`修改3.md`：作者提供的修改意见。
- `Template/`、`sources/`：模板和会议原始资料。

## 当前图表与正文引用

旧图编号以作者提供的ISPA底稿为准。旧状态图和旧数据图直接复制原PDF，图内数据、文字、箭头、坐标、事件标记及训练轮数均未修改。

| 正文图号 | 内容与来源 | 正文引用 |
|---|---|---|
| Fig.1 | 系统／威胁边界；三角色逻辑图，使用imagegen | 系统边界段落 |
| Fig.2 | 五阶段总览；参考旧Fig.3，使用imagegen | 状态控制章节开头 |
| Fig.3 | 原四状态机；旧Fig.4 | 历史与状态小节 |
| Fig.4 | 三栏分层聚合；参考旧Fig.5，使用imagegen | 聚合章节开头 |
| Fig.5(a)(b)(c) | 旧Fig.6全部三个子图 | 原训练研究第一个小节，逐个引用(a)(b)(c) |
| Fig.6(a)(b) | 旧Fig.7全部两个子图 | 组件分析小节，逐个引用(a)(b) |
| Fig.7 | 旧Fig.8异质性图 | 数据异质性小节 |
| Fig.8，附录A | 构造恢复测试，来源为控制器事件CSV | 恢复测试小节及附录 |

三张逻辑图使用内置 `image_gen.imagegen` 工具，完整提示词位于 `figures/imagegen_prompts.json`。原图来源位于 `../Figure/`。旧四状态图的直接跨级箭头属于原设计，Table 1规定当前控制器的逐级规则；图注保留此区别。探针图原ASR标签不改，正文没有将untargeted攻击柱高解释成统一targeted ASR或精度下降。旧训练图列在 `Original Training Study`，没有冒充重新运行控制器的结果。

## 构造验证与局部日志

`protocol/results/validation.json` 保存11组构造控制测试的结论及实现、配置、测试脚本哈希。`state_events.csv`、`block_events.csv`、`layer_events.csv`记录实际执行该测试得到的状态、权重与增量；它们不是CIFAR-10训练或硬件测量。

恢复测试让20个客户端从QUARANTINE开始，每次提交相同二维向量和有利审计证据：第4次产生非零贡献、第6次回到NORMAL。纯EMA最大风险序列第18次进入BLACKLIST。测试没有产生分类准确率、ASR、平台耗时或重复训练SD。

`local_evidence/`及`protocol/results/legacy_observed_events.csv`来自此前核查过的单次局部Flwr日志。缺失瞬时风险、实际权重等字段保持空值；本地代码不是完整原实验的替代品。没有因某项本地指标有利而合并不同配置或补出原消融结果。

复现命令（在本目录执行）：

```bash
./build_submission.sh
python protocol/validate.py
python protocol/plot_validation.py
```

构建脚本只输出 `ispa2026_submission.pdf`，编译中间文件在临时目录中生成并自动清理。后两条命令只执行构造控制测试及绘图，需要NumPy与Matplotlib；不会启动联邦训练或连接数据库。局部日志的只读提取命令是 `python extract_local_evidence.py`，合并已记录事件使用 `python protocol/audit_old_trace.py`，两者与构造验证分别处理。

## 原实验条件与作者确认

| 项目 | 采用口径 | 尚未确认 |
|---|---|---|
| 主结果重复次数 | 两个平台使用相同五组seed、划分和攻击安排，共十次平台—seed运行；按作者最新“这两个没区别”说明采用配对条件 | 具体seed列表、每平台统计；样本SD还是总体SD |
| 消融 18.25/95.12、2.10/48.33、0.15/21.05 | 按用户答复“2是最终的吧”和 main.tex 原标注，采用最终封禁语义 | 原始整数事件计数、分母和跨运行平均方式 |
| 状态时序与参考集合 | 按作者核查时“可以这么认为”确认采用正文约定 | 该确认不意味着局部代码自动成为完整原实现 |
| 本地数据 | 授权暂用；采用可追溯的独立单次诊断结果 | 不跨配置合并、不只选择有利指标隐藏口径差异 |

PRICAI PDF 描述轻量 CNN / 五次运行，main.tex 描述 ResNet-18 / 两个平台十次运行。现按用户确认采用后者，不混合二者的运行次数，也不自行称为十组独立数据随机化。

## PRICAI 客户端范围

核对原提交 [PRICAI PDF](</root/code/Pytorch/PaperWriting/PRICAI 2026/PRICAI_2026_paper__46.pdf>) 第 10–11 页设置及第 12 页主表：

- 训练统计池：20 个已准入客户端。30% 设置为 14 个正常 + 6 个恶意；50% 压力测试为 10 + 10。
- 准入测试额外节点：5 个没有有效证书的 Sybil + 3 个伪造低工作量的 free-rider。
- PDF 第 11 页明确说，这 8 个节点在后续统计前被拦截，后续指标在 20 个已准入客户端上计算。
- 因此全套训练/准入测试涉及的身份合计为 **28（20+5+3）**；28 是由原文两组数量相加，不是把 FL 的 K 改成 28。
- 按作者最新要求，仅在实验设置开头说明上述身份范围，删除摘要、设置表和后文的重复强调。

## 原文数值记录

下列各项的完整链路 `代码版本 → 配置 → 平台 → seed → 数据划分 → 攻击配置 → 原始日志 → 统计脚本` 均尚未完整提供。下表中的“出处”是文稿出处，不是日志路径。平台/次数按用户确认；主实验的模型/划分/攻击按原文保留；没有为任何条目编造 hash、seed、路径或置信区间。

| 稿件条目 | 保留值 | 原文出处 | 核查时处理 |
|---|---|---|---|
| 主表 FedAvg：Acc / ASR | 86.15±1.20 / 92.34±5.10 | [main.tex:516](/root/code/Pytorch/PaperWriting/main.tex:516) | 原报告均值/SD，不复算 |
| 主表 Krum：Acc / ASR | 64.20±2.80 / 12.15±0.90 | [main.tex:517](/root/code/Pytorch/PaperWriting/main.tex:517) | 同上 |
| 主表 Trimmed Mean：Acc / ASR | 71.35±2.40 / 38.60±4.20 | [main.tex:518](/root/code/Pytorch/PaperWriting/main.tex:518) | 同上 |
| 主表 FLTrust：Acc / ASR | 81.25±1.50 / 15.42±1.10 | [main.tex:519](/root/code/Pytorch/PaperWriting/main.tex:519) | 同上 |
| 主表 Trust Flow：Acc / ASR / 最终 FPR | 92.31±0.09 / 10.21±0.05 / 0.00% | [main.tex:520](/root/code/Pytorch/PaperWriting/main.tex:520) | 同上；不作为新门控规则的实证 |
| 50% 边界测试：Acc / ASR / 最终 FPR | 91.81±0.10 / 10.46±0.06 / 0.00% | [main.tex:459](/root/code/Pytorch/PaperWriting/main.tex:459) | 仅原报告压力测试，不从 Flwr-half 取数 |
| 单流 aggressive：最终 FPR / TPR | 18.25% / 95.12% | [main.tex:546](/root/code/Pytorch/PaperWriting/main.tex:546) | 不改标成 review；计数口径有待核实，表中加标记 |
| 单流 conservative：最终 FPR / TPR | 2.10% / 48.33% | [main.tex:547](/root/code/Pytorch/PaperWriting/main.tex:547) | 同上 |
| HistPerf-only：最终 FPR / TPR | 0.15% / 21.05% | [main.tex:549](/root/code/Pytorch/PaperWriting/main.tex:549) | 同上 |
| Trust Flow：最终 FPR / TPR | 0.00% / 100.00% | [main.tex:550](/root/code/Pytorch/PaperWriting/main.tex:550) | 独立的最终封禁列 |
| Trust Flow：review FPR / TPR | 14.79% / 88.33% | [main.tex:555](/root/code/Pytorch/PaperWriting/main.tex:555) | 独立 review 列，不与 0/100 混用 |
| 正常客户端最终留存 | 100% | [main.tex:486](/root/code/Pytorch/PaperWriting/main.tex:486) | 不当作实际非零权重参与率或恢复率 |
| 服务器聚合 / 聚合+审查 | 2.10 s / 4.85 s | [main.tex:607](/root/code/Pytorch/PaperWriting/main.tex:607) | 平台归属、次数、方差未知 |
| 附加报告 | 约 15 KB | [main.tex:608](/root/code/Pytorch/PaperWriting/main.tex:608) | 不当作整轮总通信量 |
| 辅助路径 / Quote+签名+监测 | 约 11 ms / 12–15 ms | [main.tex:596](/root/code/Pytorch/PaperWriting/main.tex:596) | 不相加，不泛化为两平台端到端耗时 |
| 每类 targeted ASR、测试样本数 | 原主实验未提供可统一核验的三组数 | [main.tex:395](/root/code/Pytorch/PaperWriting/main.tex:395) 定义 | 本地另有BD/CL各10,000样本，未排除目标类；分别10.21/10.22，不替代原macro |
| 实际参与率、恢复耗时、隔离前攻击权重 | 原主实验未提供 | 原文仅给最终留存和示例轨迹 | 本地有466/480正常客户端—轮次至少一层入选；无实际权重或正常隔离恢复样本 |
| 共享池/代理集消融、同证据双流对比、现代基线 | 未提供完整匹配结果 | 修改1 要求新增的实验 | 核查时未新增数字 |

### 消融分母的具体问题

若每次运行固定有 14 个正常客户端、6 个恶意客户端，共十次，并按最终二元封禁事件等权平均，则 FPR 的步进为 `100/140 ≈ 0.714286` 个百分点，TPR 步进为 `100/60 ≈ 1.666667` 个百分点。前三组消融数字不能由这一计数规则四舍五入得到。

这**不等于认定原结果错误**；可能存在其他运行数、客户端数、试验组合或加权方式，但核查时没有依据选定其中任何一种。稿件保留用户确认的最终封禁语义和原值，同时明确计数/汇总规则待核实。不能把它们擅自解释成逐轮 review 来消除矛盾。
