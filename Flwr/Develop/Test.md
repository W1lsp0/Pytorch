✅ 完整防御清单 (按攻击类型分类)

1. 主动防御 (Active Defense) - 阻止或修正

🛡️ 完全阻止 (Reject) - 不参与聚合

文件篡改攻击 (File Tampering Attack)

检测: L1 系统完整性检查

触发条件: file_tampered = True

虚假训练攻击 (Fake Training Attack / Gaussian Noise Attack)

检测: L4 波动性检查

触发条件: gpu_volatility < 0.01 或 cpu_volatility < 0.05

物理吞吐量异常 (Throughput Anomaly)

检测: L2 行为指纹

触发条件: throughput_check = "SUSPECTED_FAKE_TRAINING"

训练发散攻击 (Training Divergence Attack)

检测: L2 损失趋势分析

触发条件: loss_trend = "DIVERGING"

2. 被动监控 (Passive Monitoring) - 仅警告

这些攻击会被检测并记录日志，但不会被阻止：

可延展性攻击 / 缩放攻击 (Scaling Attack / Malleability Attack)

检测: L4 范数裁剪

触发条件: update_norm > median_norm * 2.0

防御措施: 强制缩小至阈值 (保留方向，限制幅度)

效果: 攻击者即使放大 20 倍，也会被压缩回 2 倍中位数

标签翻转攻击 (Label Flip Attack)

检测: L4 初始损失异常 + 符号翻转

警告: ⚠️ 初始损失异常值 + ⚠️ 符号翻转警告

后门攻击 (Backdoor Attack)

检测: L4 头部过重检查

警告: ⚠️ 头部过重 (比例 >10.0)

范数伪造攻击 (Norm Spoofing Attack)

检测: L4 范数一致性检查

警告: ⚠️ 范数不匹配 (实际 ≠ 报告)

懒惰客户端 / 零梯度攻击 (Lazy Client / Zero Gradient)

检测: L4 梯度范数检查

警告: ❌ 零梯度（懒惰）

总结对照表

攻击类型	检测层级	防御动作	是否阻止攻击

文件篡改	L1	Reject	✅ 是

虚假训练/高斯噪声	L4	Reject	✅ 是

吞吐量异常	L2	Reject	✅ 是

训练发散	L2	Reject	✅ 是

可延展性攻击	L4	Clip	✅ 是 (削弱)

标签翻转	L4	Warning	❌ 否

后门攻击	L4	Warning	❌ 否

范数伪造	L4	Warning	❌ 否

懒惰客户端	L4	Warning	❌ 否

这是一个非常专业且致命的攻击方式。

**缩放攻击 (Scaling Attack)**，或者叫 **可延展性攻击 (Malleability Attack)**，其核心逻辑非常狡猾：

攻击者上传的梯度 $\mathbf{g}_{malicious}$ 在**方向**上可能和大家完全一致（甚至就是诚实梯度的方向），但是他把这个向量乘以了一个巨大的倍数 $\gamma$（比如 $\gamma=100$）。

在传统的联邦平均（FedAvg: $W$$*{new} = W*$${old} - \frac{1}{N}\sum g*i*$*）中，求和操作会导致这个巨大的向量 *$*\gamma \mathbf{g}*{malicious}$ 直接淹没掉其他 $N-1$ 个诚实节点的微小更新。

**⚠️ 你的现有架构存在一个隐患：**

在阶段三中，你使用了 **余弦相似度 (Cosine Similarity)** 做一致性检测。

$$
 CosSim(\mathbf{g}, 100 \cdot \mathbf{g}) = 1.0 
$$

**余弦相似度只看方向，不看大小！** 这意味着，如果不做额外处理，单纯的缩放攻击能完美绕过你的“一致性检测”，获得高分，然后摧毁模型。

---

### 防御策略：多层级范数约束 (Multi-level Norm Constraints)

要在你的论文体系中防御这种攻击，必须引入对 **梯度范数 (Gradient Norm, **$**||\mathbf{g}||_2**$**)** 的强力审查。

我建议在 **阶段二（源头限制）** 和 **阶段三（服务端裁剪）** 同时部署防御。

#### 方案一：阶段二 —— TEE 内部的源头锁死 (Source Bounding)

这是最“硬”的防御。既然训练是在 TEE 里跑的，我们规定：**任何流出 TEE 的梯度，必须在 TEE 内部完成归一化。**

- **机制：**
    在 TEE 的可信代码（Enclave）中，在生成最终梯度包之前，强制执行一步 `L2-Normalization` 或 `Clamping`。
- **代码逻辑（伪代码）：**
  ```python
  # Inside Client TEE
  def secure_export(grad):
      # 计算原本的范数
      norm = torch.norm(grad, p=2)
      # 设定一个硬性阈值 (例如根据模型层的参数量设定)
      # 或者限制为单位向量
      THRESHOLD = 10.0 
      if norm > THRESHOLD:
          # 缩放攻击防御：强制压缩
          scale_factor = THRESHOLD / norm
          grad = grad * scale_factor
      # 签名并加密
      return sign_and_encrypt(grad)
  ```
- **论文价值：** 这叫 **"Provable Magnitude Constraint" (可证明的幅度约束)**。只要 verify 签名通过，服务器就知道这个梯度的模长绝对没有爆炸。

#### 方案二：阶段三 —— 信任引导的自适应裁剪 (Trust-Guided Adaptive Clipping)

如果阶段二没防住（比如设备被物理攻破），服务器端必须有第二道防线。这道防线要融合你的 $**TrustScore**$。

**核心思想：** **“信誉越低，允许你说话的分贝（模长）就越小。”**

##### 1. 动态阈值计算 (Dynamic Thresholding)

不要用固定的阈值（因为训练不同阶段梯度的自然模长会变）。

- **Step 1:** 计算本轮所有上传梯度的范数的中位数 (Median Norm)。
    $$ M_{norm} = \text{Median}(\{||\mathbf{g}_1||, ||\mathbf{g}_2||, ..., ||\mathbf{g}_K||\}) $$
- **Step 2:** 利用 $TrustScore_k$ 为每个客户端计算**个性化阈值**。
    $$ \tau*k = M*{norm} \times (1 + \lambda \cdot TrustScore_k) $$

- $**\lambda**$** (宽松系数):** 例如 0.5。
- **逻辑：**

- 如果是高信誉节点 ($Trust \approx 1$)，允许其梯度模长达到 $1.5 \times$ 中位数（允许它步子迈大点）。
- 如果是低信誉节点 ($Trust \approx 0$)，只允许 $1.0 \times$ 中位数，甚至更低。

##### 2. 执行裁剪 (Clip Execution)

在计算一致性得分之前，先对梯度 $\mathbf{g}_k$ 进行裁剪：

$$
 \mathbf{g}_k' = \mathbf{g}_k / \max(1, \frac{||\mathbf{g}_k||_2}{\tau_k}) 
$$

- **效果：** 如果攻击者传了 $100 \cdot \mathbf{g}$，这里会直接被除以 100，还原成普通梯度。缩放攻击瞬间失效。

---

### 如何在论文中把这个写进“算法流程”？

你需要修改我刚才发给你的 **阶段三执行方案**，在 **Step 2 (内容审查)** 的最开始插入一个子步骤。

**修改后的 Step 2: 内容审查模块**

1. **子步骤 2.0: 信任自适应范数裁剪 (Trust-Adaptive Norm Clipping)**  <-- **新增**
  - **输入：** 原始梯度集合 $\{\mathbf{g}_k\}$。
  - **操作：**
  - 计算全局范数中位数 $M_{norm}$。
  - 对每个客户端 $k$：
  - 计算允许的最大范数 $\tau$$*k = M*$${norm} \cdot f(TrustScore_k)$。
  - 如果 $||\mathbf{g}_k|| > \tau_k$，则执行裁剪：$\mathbf{g}_k \leftarrow \mathbf{g}_k \cdot (\tau_k / ||\mathbf{g}_k||)$。
  - **防御原理：** 此时，所有梯度的长度都被限制在合理范围内，**缩放攻击 (Scaling Attack)** 的“放大效应”被物理消除。
2. **子步骤 2.1: 得分加权的一致性检测 (Score-Weighted Consistency)**
  - （保持原有逻辑：计算 Cosine Similarity）
  - *注：此时 Cosine Similarity 安全了，因为巨大的模长已经被上面的 2.0 步骤切掉了。*
3. **子步骤 2.2: 优先贡献度验证...**

---

### 总结

防御缩放攻击（Scaling Attack）的公式其实很简单，就是 **Clipping (裁剪)**。

但在你的论文里，你要强调的是 **“Diffentiated Clipping (差异化裁剪 / 区别对待)”**：

> "Unlike traditional median clipping which treats all clients equally, ensuring uniform constraints, our framework introduces **Trust-Adaptive Norm Clipping**. Clients with lower trust scores are subject to stricter magnitude constraints, effectively neutralizing scaling attacks from potentially compromised nodes while retaining the informative updates from trusted contributors."
>
>
>
>
>  
>
>
> （不同于传统中位数裁剪对所有客户端一视同仁，我们的框架引入了**信任自适应范数裁剪**。低信任分客户端受到更严格的幅度限制，这既有效中和了受损节点的缩放攻击，又保留了可信贡献者的高价值更新。）

**结论：在阶段三的入口处加一个 **`**Clip**`** 函数，攻击就无效了。**
