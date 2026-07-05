可以把 EDR/HIDS 定位成 **客户端阶段一的“宿主侧安全传感器”**：TEE/TMAA 负责“可信采集、签名和上报”，EDR/HIDS 负责“看见 TEE 外部的系统行为”。两者关系是：

`TEE 根信任 + TMAA 可信代理 + HIDS/EDR 行为遥测 -> TrustReport -> 熵分析/Kalman -> TrustScore`

它主要辅助 Phase One 做这些事。

**1. 进程与训练环境完整性监控**

检测客户端是否真的在运行预期训练进程，而不是伪造训练结果。

可增加特征：

```latex
proc\_hash,\ proc\_tree,\ cmdline,\ module\_hash,\ container\_id
```

能发现：

- 训练脚本被替换
- Python 包、动态库、模型代码被篡改
- 非法子进程注入训练流程
- free-rider 伪装低负载训练

对应论文表述可以写成：HIDS monitors process lineage and executable/library integrity, while TMAA signs the digest inside the TEE.

**2. 文件完整性与数据集访问监控**

辅助发现数据投毒、标签篡改、触发器注入。

可监控：

```latex
file\_hash,\ dataset\_manifest,\ label\_change\_rate,\ trigger\_file\_access,\ config\_diff
```

能发现：

- 标签文件异常修改
- 本地训练集被批量替换
- 恶意 trigger 图片/补丁被加载
- 配置文件中学习率、batch size、epoch 被异常修改

这对 label flipping、clean-label backdoor、semantic backdoor 都有辅助价值。

**3. 系统调用与行为序列异常检测**

这是 HIDS 很自然的功能，可以补强现在的 `instr_dist`。

现有：

```latex
\mathcal{X}_k = \{ \Delta grad, \Delta loss, instr\_dist \}
```

可以扩展为：

```latex
\mathcal{X}_k =
\{ \Delta grad, \Delta loss, instr\_dist,
syscall\_dist, proc\_tree, file\_integrity, net\_flow, resource\_usage \}
```

能发现：

- 训练期间异常读写大量非训练文件
- 异常执行 shell、下载器、注入工具
- 训练进程调用模式和正常训练明显不同
- 攻击脚本周期性修改梯度或模型参数

**4. 网络连接与外联行为监控**

EDR 在这方面更强，HIDS 也可以做轻量版。

可增加：

```latex
net\_flow,\ remote\_ip\_reputation,\ beacon\_freq,\ upload\_pattern
```

能发现：

- 客户端连接攻击者 C2
- 多个 Sybil 节点连接相同控制端
- 训练中异常下载 payload
- 上传更新之外存在异常数据外传

这个功能对 Sybil、被远程控制的恶意客户端、后门 payload 动态注入很有帮助。

**5. 资源使用与 free-rider 检测**

你文中已经有 “forged low workloads / resource fraud nodes”，HIDS/EDR 可以让这个更有说服力。

可监控：

```latex
cpu\_usage,\ gpu\_usage,\ memory\_curve,\ io\_rate,\ training\_time
```

能发现：

- 客户端几乎没训练却上传更新
- 训练时间和数据量不匹配
- GPU/CPU 使用曲线异常平坦
- 伪造 loss 或梯度统计

可以形成一个独立风险项：

```latex
r_{host,k}^{(t)} = \mathrm{Normalize}
(
\eta_1 r_{proc} + \eta_2 r_{file} + \eta_3 r_{net} + \eta_4 r_{res}
)
```

然后进入风险流：

```latex
Risk_{k}^{inst} =
\max\{r_{report}, r_{host}, r_{grad}, r_{probe}, r_{trigger}, \dots\}
```

**6. 响应动作：软隔离、降权、重新证明**

如果用 EDR，不一定只做检测，还可以作为客户端阶段一的响应器。

可以增加这些动作：

- `Re-attestation`：发现异常后要求客户端重新远程证明
- `Soft quarantine`：本轮允许上传，但不参与聚合或大幅降权
- `Process freeze`：冻结可疑训练进程，等待审计
- `Report hardening`：提高该客户端后续若干轮的监控频率
- `TrustScore decay`：将异常事件映射为 TrustScore 惩罚

不要直接写“EDR 自动删除恶意客户端”，更稳妥的是：EDR/HIDS 产生风险证据，最终由服务器的 trust-flow 决策。

**推荐加法**

我建议论文里增加一个轻量模块，叫：

```latex
TEE-anchored Host Telemetry Probe
```

或者：

```latex
HIDS-assisted Runtime Trust Measurement
```

它输出一个宿主侧风险项：

```latex
r_{host,k}^{(t)}
```

然后让它同时影响两个地方：

```latex
H(\mathcal{X}_k^{(t)})
```

和

```latex
Risk_{k}^{inst}
```

这样它既能影响 Phase One 的 `TrustScore`，又能进入 Phase Three 的 `RiskEMA`，和你现在的 trust-flow 结构完全兼容。

一句话概括：**HIDS/EDR 辅助 TEE 看见“训练进程之外”的宿主行为，包括进程、文件、系统调用、网络和资源使用；TEE 保证这些遥测可信上报，服务器再把它们转化为 TrustScore 和 RiskEMA。**
