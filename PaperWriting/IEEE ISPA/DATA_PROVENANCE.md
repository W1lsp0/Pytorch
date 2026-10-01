# Submission 数据来源与复现

当前只维护 `ispa2026_submission.tex`、`ispa2026_submission.pdf`，不另存编号稿或对照册。文献库为 `ispa2026_references.bib`。

## 文件用途

- `figures/`：当前使用的图、逻辑图提示词及聚合图展示脚本。
- `protocol/`：构造控制测试、配置、事件 CSV 和验证结果；不包含完整训练适配器。
- `local_evidence/`、`extract_local_evidence.py`：已提取的局部 Flwr 诊断资料，不代表完整论文实验。
- `old/`、`../Figure/`、`../main.tex`、PRICAI PDF：原始来源，未覆盖或改写。
- `修改.md` 至 `修改4.md`：作者提供的修改意见。
- `Template/`、`sources/`：原始模板与会议资料。

## 当前图表与正文引用

| 正文图号 | 内容与处理 | 正文引用 |
|---|---|---|
| Fig.1 | 系统与报告边界；原 imagegen 图保持，缩至 0.94 倍版心宽度 | 系统边界 |
| Fig.2 | 五阶段流程；保留当前结构 | 状态控制开头 |
| Fig.3 | 沿用作者旧状态图的圆形节点、颜色和上下分区，使用 imagegen 重构五条边并加入条件 | 历史、风险与持续转移 |
| Fig.4 | 三栏分层聚合；保留图内内容 | 聚合章节 |
| Fig.5(a)(b) | 训练实测曲线和客户端轨迹；移除 t-SNE 子图，曲线 PDF 本身不变 | 训练结果逐个引用 |
| Fig.6(a)(b) | 聚合变体和异质性；数值不变，中性标题，移除 Renorm Benefit 箭头及差值线 | 组件与数据划分逐个引用 |
| Fig.7，附录 | 构造恢复测试；保持原图，未伪装成训练曲线 | 控制验证与附录 |

状态转移表已删除；具体规则由 Fig.3 和正文给出。Fig.3 只含 NORMAL→SUSPECT、SUSPECT→QUARANTINE、QUARANTINE→BLACKLIST、QUARANTINE→SUSPECT、SUSPECT→NORMAL 五条边，BLACKLIST 表示服务器永久拒收，不表示厂商撤销 TEE 凭据。原状态图完整保留在 `../Figure/fig4_state.pdf`。

`figures/imagegen_prompts.json` 保存四张当前逻辑图的完整提示词。未采用最初生成的横排矩形状态图，采用的是作者确认可重构后生成的原圆形布局图。

Fig.5(a) 的旧标题含 “ASR Baseline”；LaTeX 仅裁去顶部 21 bp 标题带并排入中性标题，数据区域、坐标和事件不变。红线根据作者确认按实测 ASR 曲线说明，不称固定基准线，不擅自等同于每轮三类攻击宏平均。图中终点 92.30% 与主表的重复运行均值 92.31% 分开解释。

Fig.6(a) 由 `figures/plot_aggregation_comparison.py` 输出。三条数组逐项保持 `../Figure/plot_ablation_final.py` 的值和完整 0–50 轮范围；没有新插值、拟合或导入局部日志。仅改标题、删除因果箭头及差值标记；第 30 轮参考线保留。Fig.6(b) 由 LaTeX 仅覆盖旧标题所在的上方区域并排入中性标题，原 PDF、坐标轴、刻度和所有数值、曲线不变。

探针柱图的 untargeted 类别缺少可核验的统计量定义，t-SNE 缺少特征、点身份和拟合说明，两图暂不用于正文或附录效果证据；原始文件完整保留在 `../Figure/`，本目录已清理未使用的重复副本，不修改其轴标签来假装解决指标问题。

## 修改4的数据确认与未补造项目

- 作者于 2026-10-01 明确答复上述曲线“就是实测”。据此保留测量语义；原脚本中的 “Interpolated data” 注释及收敛草稿中的重构/插值事实如实记录，不因该注释单独否定作者确认，也不宣称已核验原始逐轮日志。
- 正文补充的设置来自 `../main.tex` 和作者对两平台各五次的确认。PRICAI 曾写轻量 CNN / 五次，不能自动将其每条旧曲线绑定到 ResNet-18 / 十次；具体图件的模型、划分与运行身份仍需原记录建立对应。
- 主结果表仅列作者确认的 TTFL 原报告：Acc 92.31±0.09、reported targeted ASR 10.21±0.05、最终正常客户端封禁 FPR 0.00%。这是原报告汇总，未根据单次本地日志重算，不当作修订控制器的训练成绩。
- 未恢复缺少逐运行对应关系的基线主表行；三类 ASR 的分子分母、目标类排除、C2 扰动预算、C3 属性、SD 统计脚本仍未补出。
- 原共享池为 5,000/50,000 张唯一训练图像，不能写成每客户端 10%；本地占比应为 5000/(5000+独占样本数)。Dirichlet 描述独占部分。敏感性扫描的逐客户端分配清单和池比例消融仍缺失。
- 500 张 proxy 来自 CIFAR-10 测试源划分；与最终评价及 calibration 的索引交集尚不能核验。没有凭空改为 9,500 张独立测试集，也没有宣称三者已证明不相交。
- 没有新增硬件参数、耗时、训练结果、整数封禁人数或统计显著性；没有导入新的局部日志数值。

## 原训练实现与当前控制器：内部核对

下表的代码列仅指当前可读的局部快照，**不是**已确定的原论文完整执行版本。它能发现接口差异，不能证明原论文实际运行采用了这些差异。

| 操作 | 原文／局部快照的可核对事实 | 当前控制器 | 结论 |
|---|---|---|---|
| 无同伴恢复 | 原文未完整规定；`Flwr/server/contribution.py` 单客户端回退到服务器贡献评分，`strategy.py` 有全体客户端参考兜底 | 无可用同伴时使用服务器质量与范数；隔离客户端不进入同轮同伴统计 | 不能宣称旧运行必然同伴死锁 |
| 历史与持续次数 | PRICAI 图写 HistPerf<0.26；`trust_manager.py:update_history` 使用相对/绝对信号的 EMA，风险更新另有瞬时覆盖和攻击专门分支 | 单位 Beta 证据、纯 RiskEMA、五条持续转移 | 不仅是记号变化；不能由局部代码证明全实现一致 |
| 门控分数 | `strategy.py:884` 按 raw_score 与门槛比较 | 门控用 G=F/U，权重保留 F | 需匹配训练核对效果 |
| 裁剪尺度 | `sensitivity.py` 使用常数 c_base=2.0 与敏感度 | 每参数块中位范数，空统计集用服务器块范数 | 局部快照不匹配当前尺度 |
| 权重与空集合 | `strategy.py:894` 空 survivor 跳过；权重 raw_score/(sum+1e-9)，未乘样本数 | 正权重 nF/sum(nF)，空集不更新 | 空集规则有共同点，实际权重不同 |

目前没有配置完整且可对应原结果的训练适配器，因此没有宣称完成原实现与修订实现的同配置训练对照。正文说明了这项缺口，构造测试不替代它。

## 构造验证与复现

`protocol/results/validation.json` 保存 11 组控制测试结果及源码哈希。`state_events.csv`、`block_events.csv`、`layer_events.csv` 是实际执行构造输入得到的记录，不是 CIFAR-10 或硬件测量。

集体恢复组现在含同条件双分支：20 个客户端初始 QUARANTINE、风险 0.95、历史 0.5、相同二维更新和服务器观测；服务器审计分支第 4 次恢复非零聚合、第 6 次全部 NORMAL。另一分支仅要求审计还必须具有可用同伴，十次尝试均冻结、聚合为零。两个分支分别标为 `collective_recovery`、`peer_required_recovery`。附录恢复图仍仅绘制原服务器审计轨迹，未改动。

`threshold_peer_counterexample.csv` 是故意将阈值解释为 0.74 并强制同伴的反例，原 `legacy_deadlock.csv` 已改名；不代表 PRICAI 或原训练实现确实采用该阈值。最大风险第 18 次进入 BLACKLIST 的既有构造结果保持。

`local_evidence/` 与 `legacy_observed_events.csv` 保持为先前局部日志诊断，缺失字段不补造，未作为十次运行的替代来源。

复现命令（在本目录执行）：

```bash
./build_submission.sh
PYTHONDONTWRITEBYTECODE=1 python protocol/validate.py
python protocol/plot_validation.py
python figures/plot_aggregation_comparison.py
```

构建仅更新 submission PDF，中间文件在临时目录内自动清理。后三项仅做控制测试或重现图件，不启动联邦训练或连接数据库。

## 当前交付核验

submission PDF 为 10 页；7 组图（含附录）及 3 张表均有正文引用，9 个图像依赖完整，字体均嵌入且没有 Type 3 字体。没有未定义引用、重复标签或 overfull box。LaTeX 对第 9 页仅由表格和恢复图组成的右栏发出 float-only 提示，已检查渲染，二者均位于附录且在第 10 页参考文献之前，无裁切或重叠。原始图目录、main.tex、PRICAI PDF 和 old 底稿哈希保持不变；三条聚合数组逐项不变；原有控制事件逐项保持，新增事件仅属于标记清楚的 peer-required 构造分支。

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
| 单流 aggressive：最终 FPR / TPR | 18.25% / 95.12% | [main.tex:546](/root/code/Pytorch/PaperWriting/main.tex:546) | 不改标成 review；计数口径有待核实，当前正文不列该消融行 |
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

这**不等于认定原结果错误**；可能存在其他运行数、客户端数、试验组合或加权方式，但核查时没有依据选定其中任何一种。来源记录保留作者确认的最终封禁语义和原值；因计数/汇总规则待核实，相关消融行未纳入当前正文。不能把它们擅自解释成逐轮 review 来消除矛盾。
