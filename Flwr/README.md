# TMAA-FL: 基于信任流驱动的可信边缘联邦学习防御框架 🛡️

（Trust-Stream Driven Reliable Federated Learning Framework in Edge Computing）

## 🌟 项目简介 (Project Overview)

本项目针对边缘计算环境中联邦学习（Federated Learning）面临的**设备操纵、数据投毒、合谋攻击及假冒女巫**等威胁，提出并实现了一套**基于 TEE 伴随模式的四阶段可信验证架构**。

与传统的“默认信任”模型（如 FedAvg 盲目相加）不同，TMAA-FL 坚持 **“验证后信任 (Trust but Verify)”**。系统将防御措施深度镶嵌在联邦学习生命周期的四个阶段（**训练前、训练中、聚合前、聚合时**），同时保证底层**敏感数据“绝对不用出域查验”**的零知识隐私承诺。整个策略流经由硬件隔离墙与软件数学评价的双重过滤，完成纯净参数的提取。

---

## 🏗️ 论文体系详解：如何在代码中实现这四大阶段？

这不仅是一个理论框架，它已经被严格落实为我们项目实仓中的各项代码逻辑。以下是依据论文体系架构进行的详细落位说明：

### 📌 阶段一：训练前 —— 坚如磐石的“入场门禁” (Pre-training: Gatekeeping)
**防御目标**：将“女巫节点（Sybil/大算力模拟出无数身份）”和“破败的设备（OS无保护/被 Root）”直接挡在系统之外。
**核心实现机制**：
1. **身份防伪与双重握手 (Identity Handshake)**：
   - 依赖预置于客户端 TEE（例如 Intel SGX, TrustZone 或 TPM 2.0芯片）内**物理不可导出的私钥**对注册挑战随机数（Nonce）进行签名。如果攻击者想用一台高性能 GPU 服务器模拟出 1000 个假客户端刷分，他根本拿不出 1000 把不同的真实硬件私钥，从而在第一关（网络身份防伪）便被秒杀。
2. **静态环境测量 (M_attest 评估)**：
   - 对运行时库及底层 OS 的测量散列值进行“白名单查验”。被篡改的程序如果提交梯度，系统将在 `Server` 验证时拒绝。
3. **冷启动公平机制 (Cold Start)**：
   - 系统给每一个拿到入场券的新设备预设历史名声 $HistPerf^{(0)} = 0.5$（中立启动）。这种机制防止任何恶意力量通过超低成本不断注册新账号冲垮模型。

---

### 📌 阶段二：训练中 —— 隐形裁判的“伴随四维监控矩阵” (In-training: Sidecar Monitor)
**防御目标**：彻底解决客户端“谎报军情”（假装训练、毒化数据）却又不能强行让其上传图片数据的“隐私悖论”。
**核心实现机制**（代码主战场位于 `Client/tmaa/inspector.py`）：
我们抛弃了将自检代码写在训练脚本里的做法，转而采用与云原生类似的 **伴随模式 (The Sidecar Pattern)**。TMAA 作为独立的守护进程寄生于 Worker 之外。它包含了四大审计层（L1~L4）：

*   **L1 系统完整性 (Static Integrity)**：
    *   动态守护运行时内存空间，监视是否被插入恶意 Hook 或被修改执行流。
*   **L2 行为动力学指纹 (Behavior Dynamics)**：
    *   **应对“懒惰节点与乱造梯度防线”：** 真正的深度学习具有独特极具规律的“锯齿形”负载（Data Loader 读取 $\rightarrow$ GPU 暴增向前向/反向传播进行流转）。如果是直接伪造高斯噪声梯度的攻击，GPU 幅度将会是一条死寂的直线。TMAA 将 CPU/GPU 计算方差打包进报告让其“装死”无处遁形。
*   **L3 零知识数据隐私审计 (Zero-Knowledge Audit)**：*(最精妙的数学侧写机制)*
    *   **指标 A: 信息熵 (Shannon Entropy) $\rightarrow$ 对应防范 Non-IID 和偏见**。若它家只有猫的数据，分类混乱度（熵）将趋近于 0，该指标直接反映了该局部参与全局大盘的能力。
    *   **指标 B: 聚类分离度 (Cluster Separability) $\rightarrow$ 对应防范 隐藏后门/投毒**。无需提取照片，TMAA 在本地挂载 Hook 获取分类前的特征向量，执行 K-Means(k=2) 计算轮廓分数。投了毒（强行把狗标成了猫）的图片必然会在特征空间造成双峰裂痕，抓捕这道“裂痕分”即能立刻指控其存在后门。
    *   **指标 C: 唯一性比例 (Uniqueness Ratio) $\rightarrow$ 对应 防范懒惰复制**。利用矩阵 Hash 检测大规模“复制粘贴凑数”的样本集。
    *   **所有的以上审计特征均加入拉普拉斯 DP 噪声**，确保连回传的标量特征也无法被逆向推导，守卫了终极隐私！
*   **L4 网络围栏 (Network Perimeter)**：
    *   监控 Socket，如果在模型训练中突然尝试联通非法外界 IP，视为合谋串供 P2P，直接掐断上报异常。

伴随程序在 Epoch 结束将上述四级指标整合打包为加密防伪的 **`TrustReport (可信报告)`** 伴随参数发走。

---

### 📌 阶段三：聚合前 —— 服务端的“正交双流裁决引擎” (Pre-Aggregation: Evaluation)
**防御目标**：从错综复杂的长短线名声及技术表现中剥离真理。抛弃被证明脆弱的“简单相加相乘”。
**核心实现机制**（代码分布于 `server/trust_manager.py` 及 `server/contribution.py`）：

1. **Phase 1 纯能力评估验证 (内容质量与方向判断)**：
    *   为了防止坏人抱团建立假标杆，引擎用第一步提取的系统安全分 (`TrustScore`) 作为话语权权重，合成全场的**“高信誉基准梯度” $\mathbf{g}_{ref}$**。
    *   接下来，使用 **余弦相似度夹角** 计算每一个客户端和真理梯度的拟合情况，并强制利用高斯衰减和开根号公式提取该客户端本轮的纯洁业务水平 (`ContentScore_k`)。这一步“绝不看历史身份”，做到一码归一码。
2. **Phase 2 长期声名演进流 (History Evolution)**：
    *   把刚才的单局测验成绩放入全班排名中执行高斯正态转化。并利用 Sigmoid 映射提取出超越大众基线水平的“向上红利势能”。
    *   这股势能利用经典的**指数移动平均 (EMA)** 公式灌注到服务器专属数据库的长期储蓄资产中更新为：$HistPerf_k^{(t)} = \beta\cdot HistPerf_k^{(t-1)} + (1-\beta)\cdot Signal$。这种设计让偶尔网卡失误的老玩家保得住尊严。
3. **Phase 3 加权巨兽诞生 (CompositeWeight Fusion)**：
    *   服务器按照公式实施绝杀大融合：$RawScore = (TrustScore)^\alpha \times (ContentScore)^\beta \times (HistPerf)^\gamma$。三维一体形成不可逾越的最终得分，用 Softmax 归一产生参与大盘分配的霸权参数 $CompositeWeight$。

---

### 📌 阶段四：聚合时 —— 大刀阔斧的“分层神经元手术” (Aggregation: Layer-differentiated Filtering)
**防御目标**：告别 FedAvg 的“要么全要，要么全丢”，让差生也能贡献价值，让投毒者无路可退。
**核心实现机制**（代码位于 `server/sensitivity.py` 与 `strategy.py` 中下段）：
最隐蔽的后门与攻击绝大多数被深埋于模型靠近尾部的决策全连接深层空间中；而表层通常只具备朴实无害的纹理提取效能。
1. **定制防线 (SensitivityScore)**：
    服务器将网络按物理顺位深度切片，并结合当前轮次的 L2 梯度范数振幅厚度算出该层的危险系数与隐私层级（即这层不能随便让普通人动）。
2. **定制门槛 (InclusionThreshold)**：
    为每个敏感层制定拦截要求，越深越核心的网络部位，要求的门槛底线飙升。
3. **细粒度剥夺 (Layer Exclusion)**：
    一旦该节点刚才在**阶段三**拿到的 $CompositeWeight$ 达不到深层敏感区域的 Threshold 标准，系统将如庖丁解牛般**强行将这部分深层权重矩阵斩断清零**！而前面那些浅提取的无害模块则按比例吸收融合。这做到了安全隔离下的极致包容！

---

## 💻 目录与模块导航 (Code Structure Map)

整个框架的代码脉络完全围绕四大阶段重构分布：

*   **`Develop/`（理论中枢）**：论文逻辑演进文件，涵盖阶段 1~3 的严密数学论证及算法设计。
*   **`Client/`（阶段一、阶段二战区）**：
    *   `client.py`：标准的 Flower 节点通信框架。
    *   `tmaa/inspector.py`：包含 L3（香农熵、差异聚类等）和 DP 噪声注入的最核心“伴随式零知识测量审计器”。
*   **`server/`（阶段三、阶段四战区：判决与操刀大厅）**：
    *   `strategy.py`：整个系统的核心主调度逻辑网关（重写并覆盖了 `fl.server.strategy.FedAvg`）。
    *   `trust_manager.py`：控制着双流解耦中的 L1/L2 惩戒信誉以及最关键的 EMA $HistPerf$ 跨服记忆计算。
    *   `contribution.py`：基于高信誉参考基准线的 L3 $ContentScore$ 方向与幅值贡献计算模块。
    *   `sensitivity.py`：执行第四阶段，精算网络矩阵各深度的门禁分数。
    *   `audit.py`：审计展示器，输出拦截那些投毒层与女巫账户的炫酷操作日记。

---

## 🛠️ 怎么把跑起来验证？ (How to Run)

项目的架构已经充分轻量解耦。所有的复杂元操作都通过矩阵操作转化为了可被纯 CPU / 单 GPU 高效解析的 NumPy/PyTorch 语法结构。

1. **环境准备**：
   挂载您拥有基础运算能力的 Python 底座，如 Conda 提供的运行支撑：
   ```bash
   /root/miniconda3/envs/pytorch/bin/python -m pip install -r requirements.txt
   ```

2. **核心服务端调度预热**：
   可直接通过指令，独立跑测重构分化好的控制枢纽与聚合网关是否有库冲突：
   ```bash
   /root/miniconda3/envs/pytorch/bin/python -m py_compile ./server/*.py
   ```

3. **进入战场 (Simulation Start)**：
   若需直接一览这四级联动下精准屏蔽乱杀的盛况，开启联邦演练：
   ```bash
   /root/miniconda3/envs/pytorch/bin/python run_simulation.py
   ```
   *(您将能在终端实时查看哪些因聚类分离存在后门或 CPU 波形平直而导致 TrustScore 跌穿的客户端，在被丢进大熔炉前夕，如何被按参数层层切断截留！)*
