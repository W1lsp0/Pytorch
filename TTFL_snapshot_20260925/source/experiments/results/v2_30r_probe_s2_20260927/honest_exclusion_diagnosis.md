# 正常客户端误排除诊断

合并三个场景和两个开发种子；每次运行分别按配置剔除攻击客户端。run-client 为一次运行中的一个客户端，不是独立受试者。分组采用保存的真实划分标签，不使用客户端自报熵。

| 探针条件 | 方法 | 分片组 | 正常 run-client 数 | 完全排除客户端-轮比例 | 观测到黑名单拦截的 run-client 数 | 黑名单拦截客户端-轮数 |
|---|---|---|---:|---:|---:|---:|
| off | single_stream | iid | 56 | 0.00% | 0 | 0 |
| off | single_stream | moderate | 30 | 27.56% | 0 | 0 |
| off | single_stream | extreme | 30 | 29.89% | 0 | 0 |
| off | ttfl | iid | 56 | 0.00% | 0 | 0 |
| off | ttfl | moderate | 30 | 10.11% | 0 | 0 |
| off | ttfl | extreme | 30 | 9.78% | 0 | 0 |
| on | single_stream | iid | 56 | 17.98% | 0 | 0 |
| on | single_stream | moderate | 30 | 51.44% | 6 | 98 |
| on | single_stream | extreme | 30 | 49.22% | 6 | 151 |
| on | ttfl | iid | 56 | 0.00% | 0 | 0 |
| on | ttfl | moderate | 30 | 30.33% | 6 | 114 |
| on | ttfl | extreme | 30 | 33.00% | 6 | 149 |

开启探针时正常 run-client 的首次黑名单拦截原因计数：

- risk_ema_above_0.90_for_4_rounds: 15
- risk_soft_isolation_for_8_rounds: 9

首次黑名单拦截通常晚于作出封禁决定的轮次，不能把两者混为一谈。未到下一轮即结束的封禁也可能不在该计数中。

代码审查线索：原始触发器分数是补丁图片的目标类概率和命中率加权和（0.7/0.3），没有干净图片的同模型对照。无攻击也可能因目标类偏好被评为异常；旧日志没有干净目标类分数，因此这只是待检验机制解释。
下一项候选：以同一批图片、同一客户端模型上的正向分数增量 max(0, patched_score - clean_score) 代替原始分数，保持其他风险和封禁阈值不变。SVD 仍按旧实现取最后一次左上补丁前向特征，单独标为后续消融问题；本次不同时调整它。
