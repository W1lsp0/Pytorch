
## 2026-09-29 V12 配对补测与持久监控

V11 两端25个运行已完成。V12首批8项中7项有效完成（其中本地持续后门s20240932由完整30轮日志恢复收尾，completion明确标记恢复）；本地延迟后门s20240932于第22轮因OOM失败，只完成21轮，禁止纳入最终比较。OOM日志包含额外进程约8.3GiB占用；不能将其直接归因于新增探针计算。V12的低熵+低准确率信号复用已有探针输出，并未新增模型前向。

撤回临时 `source/experiments/results/v12_low_entropy_guard_seed20240933/v12_guard_summary.md/json`（保留 `.invalidated`）：它把s20240933本地候选与远端基线混配，并将无攻击基线错误用于延迟后门。由 `summary_invalidated.json` 标记；这些差值不得用于算法结论或论文。V11 `reports/remote_t4` 混用了t5的none/backdoor，只能视为混合阈值组，不能当作完整t4矩阵。

已启动严格匹配补测；原始V12训练快照冻结于 `source/experiments/results/v12_matched_monitor/source`，不修改进行中的算法。新队列本地GPU0/1/3/4分别运行s33无攻击基线、s33持续后门基线、s32延迟候选重跑、s33延迟基线；GPU3之后接续s33延迟候选。本地GPU2存在其他共享负载，暂不使用。远端GPU0继续原s33延迟基线，GPU1/2补s33无攻击/持续后门候选。两端s33均各自配对，不跨环境求算法增益。

持久化监督器：本地PID 910962、远端PID 12669；中央归档监控PID 914963（PID仅为此次快照，以实际存活/心跳为准）。每30秒检查，每5分钟同步远端证据，完成后自动生成配对审计。源脚本：`experiments/report_v12_matched.py`、`experiments/watch_v12_matched.py`；4个配对回归测试通过，拒绝错场景、错种子、错Python环境。

中央入口：`source/experiments/results/v12_matched_monitor/health.json`、`health_events.jsonl`、`pairs.json`、`matched_report.md/json`、`watcher.log`。两端节点监控：各自 `v12_low_entropy_guard_seed20240932/control`（本地）和 `v12_low_entropy_guard_seed20240933/control`（远端）。监督器有独占锁，禁止重复启动。中央closeout的paired_reports_complete仅代表审计完成，goal_achieved仍为false，不代表研究目标完成。

s32与V11对比仅列historical_reference（训练代码版本不同）；s33正式配对须校验训练源、初始化、完整分片、攻击时序和环境路径。V12四个开关组合改变，不能把整体收益归因于单独低熵保护。新方法仍默认关闭，目标尚未完成。

用户指出论文目标路径为 `PaperWriting/main_en.tex`。本轮仅监测，未更新论文结论；现有论文实验设定/数值与当前CIFAR10开发矩阵存在差异，待正式证据审计后单独核对。
