# 实验相关对话导出

> 本文件只保留当前对话中与实验协议、源码实验修复、实验运行、结果审计和论文实验结论有关的内容。远程登录、Conda、PyTorch 环境重建和远程 GPT 使用内容不包含在内。

## 对话 1

**用户：** 看看当前进度

**用户：** 论文包呢

**用户：** review.txt 论文返回意见在哪

**用户：** 给我看一下当前的源码 分析一下

**用户：** 需要更详细的分析

**用户：** 记录到md

**助手执行结果：** 创建源码分析文档 `源码详细分析.md`，记录当前实现、训练流程、数据划分、信任状态、探针、聚合、指标、随机性、数据库和 TEE 模拟等问题。

## 对话 2

**用户提供的实验整改方向：**

修复顺序确定为：

> 修复实验协议 → 验证双流贡献 → 补齐必要实验 → 重写论文。

论文核心问题应收缩为：正常客户端可能长期低相似度，而恶意客户端可能先积累信誉再突然攻击，因此长期贡献 `HistPerf` 和短期风险 `RiskEMA` 不应由同一个状态承担。

主贡献暂定为：

1. 双流状态建模；
2. 风险驱动聚合控制；
3. 可复现实验与系统开销分析。

实验协议要求包括：

- 服务器代理集从训练集划出，测试集只用于评测；
- 主设置移除所有客户端共享训练池；
- 每个客户端保存样本索引并避免训练样本重叠；
- 客户端实际 epoch 与报告 epoch 一致；
- 测试损失按样本数加权；
- 主结果评估聚合后的全局模型；
- 攻击真值与防御输入分离；
- 防御模块不能读取恶意客户端身份或攻击类型；
- 统一 HistPerf、RiskEMA 初值、递推、阈值和状态转换；
- 记录每轮每层幸存者数量、权重、裁剪、空集回退；
- 比较 FedAvg、FLTrust、Single-Stream 和 TTFL；
- 运行无攻击、持续后门、延迟后门；
- 报告干净准确率、每种攻击 ASR、误封率、检测延迟和恢复时间；
- 已知触发器探针必须和未知攻击检测分开报告；
- TEE 暂时降为软件模拟扩展，不能宣称真实硬件保证。

**助手执行结果：** 创建 `实验协议修复与论文重构计划.md`，并开始按上述顺序修改源码和执行实验。

## 对话 3

**用户：** 帮我执行吧

**助手执行结果：** 完成第一批源码修复：

- 新增 `source/config.py` 集中管理实验配置和随机种子；
- 客户端共享池默认设置为 0；
- 服务器代理集改为 CIFAR-10 训练集独立子集；
- 增加攻击起始轮次；
- 修复训练 epoch 与报告 epoch 不一致；
- 修复测试 loss 样本加权；
- 默认关闭隐式预训练权重下载；
- 增加模拟签名校验；
- 数据库配置改为环境变量；
- 支持 `fedavg`、`fltrust`、`single_stream`、`ttfl`；
- 默认关闭已知触发器探针和客户端自报决策；
- 禁用默认全量 PCA，避免内存问题；
- 新增 `source/experiments/dev_matrix.json` 和开发矩阵执行器。

静态检查通过：Python 编译、Shell 语法、JSON 校验、签名校验、数据划分和模型前向测试均通过。

## 对话 4：四种方法无攻击烟雾测试

**实验配置：** 4 客户端、1 轮、1 个本地 epoch、CIFAR-10、随机初始化、无攻击、种子 `20240925`。

结果：

| 方法 | Accuracy | Backdoor ASR | Clean-Label ASR |
|---|---:|---:|---:|
| FedAvg | 0.2278 | 0.2257 | 0.2365 |
| TTFL | 0.2268 | 0.2034 | 0.2110 |
| Single-Stream | 0.2292 | 0.1852 | 0.1907 |
| FLTrust | 0.2207 | 0.2045 | 0.2110 |

**解释：** 这些只验证执行链路，不是论文结果。

文件：`source/experiments/smoke_results.json`。

## 对话 5：持续后门和延迟后门烟雾测试

持续后门配置：4 客户端、2 轮、C1 后门、投毒比例 0.2、攻击第 1 轮启动。

结果：第 1 轮 ASR 0.3257，第 2 轮 ASR 0.1191；攻击评估链路有效。

延迟后门配置：4 客户端、2 轮、C1 后门、攻击起始轮 2。

结果：第 1 轮攻击未激活，第 2 轮激活；该批次主要验证调度路径。

文件：

- `source/experiments/attack_schedule_smoke.json`
- `source/experiments/results/smoke_ttfl_backdoor_4c_2r/`
- `source/experiments/results/smoke_ttfl_delayed_backdoor_4c_2r/`

## 对话 6：第一批开发矩阵

**配置：** 4 客户端、2 轮、1 个本地 epoch、无攻击、种子 `20240925`，四种方法。

结果：

| 方法 | 第 1 轮 Accuracy | 第 2 轮 Accuracy | 第 2 轮 Backdoor ASR |
|---|---:|---:|---:|
| FedAvg | 0.2368 | 0.2737 | 0.0277 |
| FLTrust | 0.2249 | 0.3017 | 0.0474 |
| Single-Stream | 0.2249 | 0.2986 | 0.0415 |
| TTFL | 0.2257 | 0.3021 | 0.0444 |

所有运行成功。由于规模小、轮数少，只用于执行协议和日志解析。

文件：`source/experiments/results/dev_batch_20260925/summary.json`。

## 对话 7：持续后门开发矩阵

**配置：** 4 客户端、2 轮、C1 第 1 轮启动、投毒比例 0.2、种子 `20240925`。

| 方法 | 第 1 轮 ASR | 第 2 轮 ASR | 第 2 轮 Accuracy |
|---|---:|---:|---:|
| FedAvg | 0.3254 | 0.1181 | 0.2925 |
| FLTrust | 0.2967 | 0.0973 | 0.2978 |
| Single-Stream | 0.2769 | 0.1091 | 0.2954 |
| TTFL | 0.2980 | 0.1292 | 0.2995 |

四种方法均成功运行，攻击评估链路有效，但不能据此做最终优越性结论。

文件：`source/experiments/results/dev_batch_backdoor_20260925/summary.json`。

## 对话 8：12 轮延迟后门

**配置：** TTFL、4 客户端、12 轮、C1 第 11 轮启动、投毒比例 0.2、默认探针轮换。

- 第 10 轮 `attack_active=false`；
- 第 11、12 轮 `attack_active=true`；
- C1 保持 `NORMAL`；
- C1 每轮 122 层全部参与；
- 第 11 轮 ASR 0.1177，未形成强攻击信号。

结论：当前投毒比例和攻击窗口太弱，不能用来评价延迟攻击防御。

## 对话 9：强度校准

**配置：** TTFL、4 客户端、6 轮、C1 第 3 轮启动、投毒比例 1.0、已知触发器探针关闭。

结果：

- 第 3 轮 ASR 0.9229；
- 第 5 轮 C1 进入 `SUSPECT`；
- 第 5、6 轮仍采纳 122 层；
- 第 6 轮 ASR 0.4529。

结论：攻击器可以产生强信号，但默认探针和当前隔离逻辑没有及时阻断全部更新。

文件：`source/experiments/results/dev_ttfl_calibration_rate1_20260925/summary.json`。

## 对话 10：强延迟攻击负对照

**配置：** TTFL、4 客户端、12 轮、C1 第 11 轮启动、投毒比例 1.0、已知触发器探针关闭、轮换值 5。

结果：

- 第 11 轮 ASR 0.9091；
- C1 保持 `NORMAL`；
- 第 11、12 轮仍采纳 122 层。

结论：默认低频/未知探针不能及时识别强后门。

文件：`source/experiments/results/dev_ttfl_delayed_rate1_12r_20260925/summary.json`。

## 对话 11：每轮已知触发器探针

**配置：** TTFL、4 客户端、6 轮、C1 第 3 轮启动、投毒比例 1.0、`ENABLE_KNOWN_TRIGGER_PROBE=1`、`HEAVY_PROBE_ROTATE_MOD=1`。

结果：

- 第 3 轮 ASR 0.8976；
- 第 4 轮 C1 进入 `SUSPECT`；
- 第 5、6 轮 C1 采纳层数为 0；
- 第 6 轮 ASR 0.0858；
- 第 6 轮 Accuracy 0.3810。

结论：在服务器知道触发器并每轮执行探针时，风险流可以及时限制当前更新。不能据此宣称未知触发器泛化。

文件：`source/experiments/results/dev_ttfl_probe_every_round_rate1_6r_20260925/summary.json`。

## 对话 12：探针敏感性对照

生成文件：`source/experiments/results/probe_sensitivity_comparison.md`。

| 配置 | 最终 ASR | C1 最终采纳层数 |
|---|---:|---:|
| 默认轮换探针 | 45.29% | 122 |
| 每轮已知触发器探针 | 8.58% | 0 |

结论：效果明显依赖已知触发器探针和执行频率，必须作为假设敏感性报告。

## 对话 13：Single-Stream 公平对照

**配置：** 与每轮已知触发器 TTFL 完全相同：4 客户端、6 轮、C1 第 3 轮启动、投毒比例 1.0、每轮探针。

结果：

| 方法 | 第 3 轮 ASR | 第 6 轮 ASR | 第 6 轮 Accuracy | C1 第 5 轮采纳层数 |
|---|---:|---:|---:|---:|
| TTFL | 89.76% | 8.58% | 38.10% | 0 |
| Single-Stream | 90.87% | 9.07% | 38.66% | 0 |

结论：两者都能隔离强后门，当前实验没有证明双流明显优于单流。后续必须测试正常 Non-IID 客户端保护、弱攻击和恢复行为。

文件：`source/experiments/results/dual_stream_probe_comparison.md`。

## 对话 14：弱后门

**配置：** TTFL、4 客户端、6 轮、C1 第 3 轮启动、投毒比例 0.2、每轮已知探针。

结果：

- C1 第 6 轮才进入 `SUSPECT`；
- 第 6 轮仍采纳全部 122 层；
- 最终 ASR 0.1202；
- 最终 Accuracy 0.3826。

结论：`SUSPECT` 是软风险状态，不等同于已经阻断攻击。

文件：`source/experiments/results/dev_ttfl_probe_every_rate02_6r_20260925/summary.json`。

## 对话 15：攻击停止后的恢复

新增参数：`ATTACK_STOP_ROUND`。

**配置：** TTFL、4 客户端、8 轮、C1 第 3–5 轮攻击、第 6 轮停止、投毒比例 1.0、每轮已知探针。

结果：

- 第 4 轮进入 `SUSPECT`；
- 第 5 轮起 C1 的 122 层全部排除；
- 第 6–8 轮 `attack_active=false`；
- 第 8 轮进入 `QUARANTINE`；
- 第 8 轮 ASR 0.1222。

结论：攻击停止后不会立即恢复，因为客户端模型仍然保留触发器行为。恢复时间必须定义为重新获得聚合资格所需轮数。

文件：`source/experiments/results/dev_ttfl_recovery_rate1_8r_20260925/summary.json`。

## 对话 16：状态机回归测试

新增：`source/experiments/test_recovery_state.py`。

测试构造一个已经隔离的客户端，然后连续输入干净风险证据：

- 风险 EMA 下降；
- soft streak 衰减；
- C2 memory score 下降到 0；
- `risk_isolated` 最终变为 false。

测试通过，说明状态机存在可达的释放路径；真实实验仍需报告实际恢复轮数。

## 对话 17：机器可读审计

新增服务器文件：`log/round_metrics.jsonl`。

每轮记录：

- 探针覆盖数量；
- 已知触发器探针开关；
- 探针轮换频率；
- NORMAL/SUSPECT/QUARANTINE 数量；
- 隔离客户端数量；
- 实际聚合客户端数量；
- 层数；
- 每个客户端采纳层数、拒绝层数、平均裁剪比例。

新增：`source/experiments/analyze_run.py`，生成 `analysis_summary.json`。

审计格式烟雾测试通过：2 轮无攻击运行中，实际聚合客户端数均为 4，隔离数均为 0。

## 当前实验结论边界

可以保留：

- 双流把长期贡献和短期风险分开建模；
- 已知触发器且每轮探针时，可以快速隔离强后门；
- `SUSPECT` 与实际聚合资格是不同概念；
- 攻击停止不代表客户端立即恢复。

不能声称：

- 未知触发器泛化已被证明；
- 真实 TEE 硬件安全已被测量；
- 双流已经显著优于 Single-Stream；
- `SUSPECT` 必然阻断当前轮更新；
- 默认低频探针可以及时发现所有强攻击。

## 待执行实验

1. 正常 Non-IID 客户端保护：统计正常客户端逐轮完全排除率、分层部分参与率和累计聚合权重。
2. TTFL 与 Single-Stream 的弱攻击公平对照。
3. 更长的干净恢复窗口，计算停止攻击后的恢复轮数。
4. 固定探针假设后，运行 20 客户端、多种子开发矩阵。
5. 再补正式基线、第二数据集和系统开销实验。
6. 最后重写论文摘要、方法、实验、图表和限制。


## 2026-09-28 续跑入口更新

最新详细记录见 `TTFL_snapshot_20260925/实验协议修复与论文重构计划.md` 第十九至二十二节。下面是当前后台批次的交接信息；前面的待办与历史结论不能替代新记录。


### 独立种子有效批次与持续监控交接（2026-09-28）

当前唯一有效的 v8 批次：`source/experiments/results/v8_cross_channel_exclusive_seed20240929`，监督器 PID 317684，使用 `/data1/anaconda3/envs/W1lsp0/bin/python`。基线三个场景独占 GPU 0/1/2，候选 none/backdoor 独占 GPU 3/4，候选 delayed_backdoor 在队列中等待首张释放的卡；共 6 项、最多 5 项并行，每项 30 轮。不要重复启动监督器，也不要将已作废的原始或 _retry 目录日志作为本批状态。

后台监督器每 30 秒写 `monitor_status.json` 和 `monitor_events.jsonl`；所有运行完成后自动汇总、协议审计、隔离诊断和配对报告。以 `closeout.json` 与 `monitor_status.json` 的 verified_complete 判断最终审计是否完成。候选仍默认关闭；运行中不修改训练代码。

本次交接快照时间：2026-09-28T09:03:16.008501+08:00；警告：[]。
- baseline / none: running，fit=2，evaluate=2，audit_round=2。
- baseline / backdoor: running，fit=2，evaluate=2，audit_round=2。
- baseline / delayed_backdoor: running，fit=2，evaluate=2，audit_round=2。
- candidate / none: running，fit=2，evaluate=2，audit_round=2。
- candidate / backdoor: running，fit=2，evaluate=2，audit_round=2。
- candidate / delayed_backdoor: queued，fit=0，evaluate=0，audit_round=0。


## 2026-09-28 v8 独立种子收尾


## 二十三、跨通道候选独立种子收尾（2026-09-28，已完成）

独占 GPU 批次 `source/experiments/results/v8_cross_channel_exclusive_seed20240929` 已完成 6/6 项：基线 none/backdoor/delayed_backdoor 与候选 none/backdoor/delayed_backdoor，各 30 轮、20 客户端、1 epoch、种子 20240929。每项 fit/evaluate 为 20 个结果、0 failures；两套协议审计 `run_count=3` 且无失败。监督器自动完成隔离诊断与配对报告，收尾状态为 `closeout.json: complete`，训练进程已退出，GPU 已释放。

候选开关仍是两个干预点：soft gate 的额外证据要求（soft_strong 绕过保留）和 C2 quarantine hit 要求；额外通道没有统计独立性证明。因此这是有明确范围的配对开发验证，不是严格单因素机制消融。

独立种子 20240929 的基线 → 候选结果：

- 无攻击：最终准确率 56.70% → 57.11%，最终 ASR 8.28% → 6.71%；正常客户端完全排除 46/600 → 21/600，明确风险隔离 46 → 5。
- 持续后门：最终准确率 54.46% → 53.72%，最终 ASR 13.09% → 14.00%，攻击窗口平均 ASR 20.69% → 21.05%；正常客户端完全排除 45/570 → 26/570，明确风险隔离 45 → 3；恶意客户端两边均未明确隔离。
- 延迟后门：最终准确率 54.44% → 54.91%，最终 ASR 10.82% → 12.64%，攻击窗口平均 ASR 14.61% → 15.21%；正常客户端完全排除 75/570 → 18/570，明确风险隔离 53 → 3；基线恶意客户端在第 16、30 轮隔离，候选在 30 轮内未隔离。

该独立种子支持候选明显降低正常客户端误排除，但代价是持续/延迟后门攻击窗口 ASR 和最终 ASR 上升，且延迟攻击的恶意隔离能力消失。因此候选不采用为默认方案；`RISK_CROSS_CHANNEL_GUARD` 保持默认关闭。完整校验与数值见候选目录 `cross_channel_guard_report.md/json`、两套 `protocol_audit.json`、`closeout.json`。后续应优先改进风险证据设计并重新进行独立验证，不应把本批结果表述为全面安全改进。


## v9 风险观察期候选监测交接（2026-09-28）

有效批次：`source/experiments/results/v9_risk_soft_probation_matrix_seed20240930_retry`。监督器 PID 386420，使用 `/data1/anaconda3/envs/W1lsp0/bin/python`，每 30 秒持续更新状态。原不带 `_retry` 的批次因误用系统 Python 缺少 flwr 而启动失败，已作废保留。

候选 `RISK_SOFT_PROBATION=1` 保留软风险状态及风险降权，改变参考集合和聚合集合的风险排除规则；黑名单/C2 隔离、Hist 隔离和层门槛仍存在，不能表述为只有黑名单/C2 才能阻断，也不能把 risk_isolated 或监控 isolated_now 等同于实际阻断。两套均固定 clean_delta、guard=0、衰减幂1，种子20240930是开发种子。

本次仅修正离线报告，未改运行中的训练源码。报告新增逐恶意客户端完全排除轮次、攻击窗口内首次排除和攻击前排除标记，同时呈现风险标记；2项语义测试通过。6个训练快照与冻结哈希一致，3组配对的训练源码、初始化、完整分片和协议一致，证据为 paired_preflight.json，complete=false 表示训练尚未完成。所有已观察的训练/评估聚合记录均为20个结果、0 failures。

最新监测：2026-09-28T18:41:09.912679+08:00，警告 []。
- baseline / none：success，fit/evaluate/audit=30/30/30，GPU 0。
- baseline / backdoor：success，fit/evaluate/audit=30/30/30，GPU 1。
- baseline / delayed_backdoor：success，fit/evaluate/audit=30/30/30，GPU 2。
- candidate / none：success，fit/evaluate/audit=30/30/30，GPU 3。
- candidate / backdoor：success，fit/evaluate/audit=30/30/30，GPU 4。
- candidate / delayed_backdoor：running，fit/evaluate/audit=21/21/21，GPU 3。

监督器在全部运行结束后自动汇总、协议审计并运行 report_risk_soft_probation.py，生成 candidate/risk_soft_probation_report.md/json 和 closeout.json。随后必须解读正常完全排除、攻击窗口平均/峰值ASR、准确率和实际恶意阻断，未达标继续找方法；不能把新候选已启动等同于实验目的完成。

## 2026-09-29 V12 配对补测与持久监控

V11 两端25个运行已完成。V12首批8项中7项有效完成（其中本地持续后门s20240932由完整30轮日志恢复收尾，completion明确标记恢复）；本地延迟后门s20240932于第22轮因OOM失败，只完成21轮，禁止纳入最终比较。OOM日志包含额外进程约8.3GiB占用；不能将其直接归因于新增探针计算。V12的低熵+低准确率信号复用已有探针输出，并未新增模型前向。

撤回临时 `source/experiments/results/v12_low_entropy_guard_seed20240933/v12_guard_summary.md/json`（保留 `.invalidated`）：它把s20240933本地候选与远端基线混配，并将无攻击基线错误用于延迟后门。由 `summary_invalidated.json` 标记；这些差值不得用于算法结论或论文。V11 `reports/remote_t4` 混用了t5的none/backdoor，只能视为混合阈值组，不能当作完整t4矩阵。

已启动严格匹配补测；原始V12训练快照冻结于 `source/experiments/results/v12_matched_monitor/source`，不修改进行中的算法。新队列本地GPU0/1/3/4分别运行s33无攻击基线、s33持续后门基线、s32延迟候选重跑、s33延迟基线；GPU3之后接续s33延迟候选。本地GPU2存在其他共享负载，暂不使用。远端GPU0继续原s33延迟基线，GPU1/2补s33无攻击/持续后门候选。两端s33均各自配对，不跨环境求算法增益。

持久化监督器：本地PID 910962、远端PID 12669；中央归档监控PID 914963（PID仅为此次快照，以实际存活/心跳为准）。每30秒检查，每5分钟同步远端证据，完成后自动生成配对审计。源脚本：`experiments/report_v12_matched.py`、`experiments/watch_v12_matched.py`；4个配对回归测试通过，拒绝错场景、错种子、错Python环境。

中央入口：`source/experiments/results/v12_matched_monitor/health.json`、`health_events.jsonl`、`pairs.json`、`matched_report.md/json`、`watcher.log`。两端节点监控：各自 `v12_low_entropy_guard_seed20240932/control`（本地）和 `v12_low_entropy_guard_seed20240933/control`（远端）。监督器有独占锁，禁止重复启动。中央closeout的paired_reports_complete仅代表审计完成，goal_achieved仍为false，不代表研究目标完成。

s32与V11对比仅列historical_reference（训练代码版本不同）；s33正式配对须校验训练源、初始化、完整分片、攻击时序和环境路径。V12四个开关组合改变，不能把整体收益归因于单独低熵保护。新方法仍默认关闭，目标尚未完成。

用户指出论文目标路径为 `PaperWriting/main_en.tex`。本轮仅监测，未更新论文结论；现有论文实验设定/数值与当前CIFAR10开发矩阵存在差异，待正式证据审计后单独核对。

## 2026-09-29 V13 layer-gate causal candidate

V12 配对补测仍在进行，未提前抢占共享 GPU。对已完成 V12 运行的逐轮审计显示，很多正常客户端的 `included_layers=0` 来自逐层 RawScore 准入门槛，而不是低熵保护：RawScore 使用 `trust^3 × content × history^0.5`，常落在 0.04--0.08；原门槛 `0.05 + 0.15*S_total` 可达约 0.20。V13 因此只把逐层门槛系数改为可配置并从 0.15 降到 0.05，保持 V12 的四个风险开关、探针、攻击时序和训练参数相同。

V13 代码已加入：`server/sensitivity.py` 的 `TTFL_LAYER_GATE_LAMBDA`；运行清单记录 `layer_gate_lambda` 并检查恢复配置；重探针只有在前向、准确率和熵成功后才计为 `heavy_probed`；低熵连续计数在未匹配或未测量轮次重置，不再用衰减伪造连续证据。默认系数仍为 0.15，当前 V12 冻结源未被修改。

V13 计划：本地主机种子 20240934、远端主机种子 20240935，各自对 none/backdoor/delayed_backdoor 做基线 0.15 与候选 0.05 的同主机配对，共 12 个 30 轮运行。V12 全部终止后，`launch_v13_after_v12.py` 自动启动本地/远端监督器；`watch_v13_layer.py` 同步远端结果并运行严格配对审计。结果入口：`TTFL_snapshot_20260925/source/experiments/results/v13_layer_gate_monitor`。V13 仍明确 `goal_achieved:false`，只有在正常误排除下降且后门指标不出现不可接受恶化时才进入下一候选。

## 2026-09-29 V12完成，V13改为按空闲GPU动态调度

V12补测8/8完成；6个同主机s33配对均通过审计，3个s32历史参考单列。V12未达标：本地延迟准确率44.05%→53.68%、正常排除48.77%→5.44%，但最终ASR6.84%→14.94%；其余严格攻击配对最终ASR也上升。不能以攻击窗口均值改善抵消最终防御退步并宣布成功。

用户要求充分利用全部可用资源：已停止旧的全批等待启动器和旧V13监控器，启用两端公共任务队列，不再按卡号固定分组。当前本地0/1/3/4与远端1/2共6卡运行V13；本地2和远端0有其他用户负载，21GiB完整任务不能安全放入剩余显存，释放后自动纳入调度。每30秒检查，启动前保留GPU槽，独占锁防重复调度，端口各任务唯一。源代码冻结；同主机配对不跨环境迁移。详见 `TTFL_snapshot_20260925/source/experiments/results/v13_layer_gate_monitor/HANDOFF.md`。

同时修复V13报告路径指向矩阵而非实际运行目录、重复字段合并、远端监控路径漏results、无验证即发完成标记等问题。12个调度/报告/配对测试通过，启动清单与两端冻结源核对一致，首轮聚合已成功。中央监控持续记录健康与审计，失败不会伪报目标完成。

更正此前断言：V12未记录可直接重建RawScore范围的字段，不能将0.04--0.08称为本批实测范围。日志阶段归因证实本地s33持续后门正常完全排除270次中221次来自逐层门槛，无攻击134次中130次；V13检验降低门槛能否改善结果，尚无有效结果。完成提醒目前只是目录里的持久文件，并不能自动唤醒助手；此前“自动提醒你”的表述不准确。

## 2026-09-29 V14 风险观察期最低权重候选已排队

V13 已开始动态运行，6个任务占用本地0/1/3/4、远端1/2；本地2和远端0由其他用户进程占用。V14 已准备为两端三臂配对：原始基线（四个V12开关全关）、V12复合参考（四开关全开且最低权重0）和最低权重候选（四开关全开、`RISK_PROBATION_WEIGHT_FLOOR=0.25`），场景为none/backdoor/delayed_backdoor。V14等待两端V13队列完成后自动启动，动态调度会按实际空闲GPU分配，不固定卡号。

V14动机来自V12阶段审计：部分正常客户端在逐层聚合前的`risk_ema_prev`达到1或至少0.9，使风险衰减因子为0或接近0；仅降低逐层门槛不能处理该路径。新候选只给观察期风险权重设下限，黑名单、C2隔离和硬隔离仍由策略独立决定。`risk_weighting.py`和4项单元测试已加入；所有结果需通过同主机、同源、同初始化、同分片、同攻击时序审计，且最终ASR/窗口ASR/峰值ASR不退化、准确率不下降、正常排除下降才通过描述性筛选。通过筛选仍不等同于论文目标完成。
