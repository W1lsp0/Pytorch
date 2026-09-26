# 第一部分：引言 (Section 1: Introduction)

**【中文原文】**
当前，随着终端设备所具备的计算能力愈加强大，越来越多的终端设备能够高效地利用本地数据支持本地模型训练，同时，为更好地以聚合多终端训练经验以支持多方模型协同优化并保护各设备的本地数据隐私，联邦学习范式被深入研究\cite{kairouz2021flsurvey}，其所具备的数据不出本地仅通过模型参数交换的特性被广泛应用于模型的分布式协同训练场景，已然成为边缘智能发展的关键支撑技术。然而，随着万物互联构成的网络环境愈加开放，基于联邦学习的经验聚合以促进模型协同优化所面临的性能瓶颈不再局限于模型结构和优化器设计层面，聚合阶段的可信性和稳健性日益成为影响整体可用性的关键因素。因为在实际应用场景中，不仅各边缘设备端的数据分布具有异构性且处理能力也有显著差异，另外，模型协同优化的各参与方相关行为也难以完全约束，这些特征在经验聚合时显然会放大统计偏移和带来安全风险。

**【英文翻译】**
Current advancements in terminal device computing power enable efficient local model training using on-device data. Meanwhile, to better aggregate multi-device training experiences for collaborative model optimization while preserving local data privacy, the federated learning paradigm has been extensively studied \cite{kairouz2021flsurvey}. Its core feature—exchanging only model parameters without offloading data—is widely applied in distributed collaborative training, serving as a critical pillar for edge intelligence. However, as the interconnected network environment becomes increasingly open, the performance bottlenecks of federated learning no longer reside solely in model architecture or optimizer design. The trustworthiness and robustness of the aggregation phase have emerged as vital factors determining overall availability. In practical scenarios, edge devices often exhibit significant heterogeneity in both data distribution and processing capabilities. Furthermore, fully constraining the behaviors of participating clients remains challenging. Such characteristics inevitably amplify statistical drifts and introduce security risks during empirical aggregation.

**【中文原文】**
在通常的联邦学习范式中，客户端完成本地数据处理及本地模型训练后，会将模型相关参数上传，服务端聚合各客户端模型参数后会下发更新后的模型参数，以此通过多轮迭代直至收敛，显然，上述流程在实际愈加开放的万物互联多边缘网络环境下，面临着多重风险。具体来说，首先，开放的训练环境缺少强制完整性约束，恶意客户端可以绕过真实训练而直接构造并上传模型参数，也会极大地影响服务端对聚合参数真实性的判断能力，一些研究工作提出了基于可信执行或可验证训练的方法\cite{lu2025tmt,zhang2025rppfl,r1_tee_integrity}，以硬件远程证明等方式保证客户端对模型训练的真实性，但仍然缺乏应对训练过程真实而模型更新却嵌入恶意特征等手段。其次，恶意客户端实施参数投毒、隐蔽后门等攻击\cite{gu2017badnets,wang2019neuralcleanse}，通过将恶意触发特征嵌入常规更新分布参数中，会显著降低单轮检测成功率，一些研究工作提出了基于时序信誉与相似性的方法\cite{cao2021fltrust,fung2020foolsgold}，通过引入跨轮信息来缓解单轮判断的不稳定问题，但对于恶意客户端前期积累信誉后期持续小幅度投毒等潜伏式攻击显然存在识别滞后问题，而且，单一信誉分与固定阈值机制对深层异常触发特征的识别能力也有很大不足。

**【英文翻译】**
In standard federated learning paradigms, clients upload parameters after completing local data processing and model training. The server then aggregates these local updates and distributes the updated global model, iterating this process until convergence. Evidently, this workflow encounters multiple vulnerabilities within the increasingly open, multi-edge interconnected network. Open training environments inherently lack mandatory integrity constraints. Malicious clients can bypass actual training, directly crafting and uploading poisoned parameters, thereby severely impairing the server's ability to verify the authenticity of aggregated updates. Several studies propose methods based on trusted execution or verifiable training \cite{lu2025tmt,zhang2025rppfl,r1_tee_integrity}, employing hardware-assisted remote attestation to ensure local training authenticity. Nevertheless, these mechanisms fail to address scenarios where the training process is genuine but the model updates are injected with malicious features. Furthermore, attackers execute parameter poisoning or stealthy backdoor attacks \cite{gu2017badnets,wang2019neuralcleanse} by embedding malicious triggers within normal update distributions, drastically reducing the success rate of single-round detection. To alleviate the instability of single-round assessments, researchers have introduced methods based on historical reputation and similarity \cite{cao2021fltrust,fung2020foolsgold} that leverage cross-round information. Yet, these approaches suffer from delayed recognition of sleeper attacks, where adversaries accumulate reputation early on before engaging in persistent, low-amplitude poisoning. Additionally, single-reputation scores combined with fixed-threshold mechanisms remain highly inadequate for identifying deep abnormal trigger features.

**【中文原文】**
另外，不同设备的非独立同分布数据（Non-IID）会增加最优更新的方向离散度，很容易模糊正常波动和异常偏移之间的边界，导致强 Non-IID 条件下鲁棒性和泛化性之间的冲突，一些研究工作提出了基于距离排斥或统计截断等的方法抑制异常更新\cite{blanchard2017krum,yin2018byzantine}，还有一些研究工作通过自适应权重调整来缓解异构影响\cite{wang2025rasa}，但强长尾分布情形下，这些方法会将合法偏移的参数更新误判为异常参数，可能导致关键异构信息被过度剔除而显著降低模型泛化能力。在实际场景中，上述执行环境更加开放、跨轮潜伏攻击、强异构统计偏移等挑战往往不会单独出现，尤其是在万物互联的边缘智能场景中，数个因素很可能相互叠加，很容易导致诸如拦截阈值收紧误杀率上升、拦截阈值放宽漏检率增加等多种难以权衡的难题。由此，如何构建覆盖全流程的统一状态建模与联动决策机制，在兼顾客户端本地模型训练的准入及可信和聚合时对客户端低误杀率且高召回率的要求下，维持模型协同优化的收敛和泛化性能成为亟需解决的关键问题。

**【英文翻译】**
The presence of non-independent and identically distributed (Non-IID) data across devices increases the directional dispersion of optimal updates. This heterogeneity easily blurs the boundary between normal statistical fluctuations and anomalous deviations, creating a conflict between robustness and generalization under strong Non-IID conditions. Certain approaches rely on distance-based exclusion or statistical truncation to suppress abnormal updates \cite{blanchard2017krum,yin2018byzantine}, while others adaptively adjust weights to mitigate heterogeneous impacts \cite{wang2025rasa}. Under severe long-tail distributions, however, such methods often misclassify legitimately drifted parameter updates as anomalies. This misjudgment can lead to the excessive exclusion of crucial heterogeneous information, significantly degrading the model's generalization capability. In real-world edge intelligence scenarios, these challenges—open execution environments, stealthy cross-round attacks, and pronounced heterogeneous statistical drifts—rarely occur in isolation. Multiple factors frequently compound, leading to intractable dilemmas such as elevated false positive rates from tightening interception thresholds or increased false negative rates when relaxing them. Consequently, establishing a unified state modeling and coordinated decision-making mechanism spanning the entire workflow remains a critical challenge. Such a mechanism must balance client admission and trustworthiness during local training with low false positive and high recall requirements during aggregation, all while maintaining the convergence and generalization performance of collaborative model optimization.

**【中文原文】**
为应对以上所述的三个主要难题，本文从软硬件协同角度提出一种基于全流程信任流的可信联邦聚合机制。该机制按照联邦学习的执行链路展开：在客户端接入和本地训练阶段，引入 TEE 远程证明、运行特征熵分析与卡尔曼滤波，形成可随轮次更新的动态准入信任分；在服务器审查阶段，基于纯净参考方向计算当轮内容质量，并进一步将客户端状态拆分为历史效用流和瞬时风险流，以贝叶斯后验和风险 EMA 分别刻画长期贡献与短时异常；在聚合阶段，依据上述信任状态执行分层风险门控、幸存者重归一化和动态裁剪，从而在抑制恶意更新的同时保留合法异构贡献，缓解 Non-IID 条件下安全性与泛化性之间的冲突。

**【英文翻译】**
To tackle the three major challenges outlined above, this paper proposes a trusted federated aggregation mechanism driven by a full-process trust flow, conceptualized from a hardware-software co-design perspective. This mechanism follows the execution pipeline of federated learning. During client admission and local training, we introduce TEE remote attestation, runtime feature entropy analysis, and Kalman filtering to formulate a dynamic admission trust score that updates across rounds. At the server auditing stage, the current-round content quality is evaluated based on a pure reference direction. The client's state is then decoupled into a historical utility flow and an instant risk flow, utilizing Bayesian posterior inference and risk EMA to separately characterize long-term contributions and short-term anomalies. During the aggregation phase, layered risk gating, survivor weight re-normalization, and dynamic clipping are executed based on these trust states. This strategy suppresses malicious updates while retaining legitimate heterogeneous contributions, effectively mitigating the tradeoff between security and generalization under Non-IID conditions.

**【中文原文】**
本文的主要贡献包括：
\begin{enumerate}
    \item \textbf{提出面向边缘客户端的 TEE 锚定动态准入机制}。以远程证明确定客户端的接入边界，再将训练过程中的梯度、损失和指令分布变化转化为熵特征，并借助卡尔曼滤波更新 $TrustScore$，使准入控制由一次性静态校验扩展为可持续演化的可信度量。
    \item \textbf{提出面向潜伏攻击的双流正交信誉演化机制}。将客户端状态拆分为历史效用流（HistPerf）与瞬时风险流（RiskEMA），分别处理长期贡献和突发异常，并以 $RawScore$ 连接内容审查、状态转移与后续聚合控制，在设定条件下兼顾恶意召回与永久误杀抑制。
    \item \textbf{设计面向强 Non-IID 的分层风险门控聚合策略}。利用服务器侧纯净参考方向、逐层安全敏感度和动态 L2 裁剪，在网络不同层采用差异化准入门槛与幸存者权重重归一化，降低深层后门透传风险，同时保留合法长尾节点的有效更新。
    \item \textbf{完成混合攻击场景下的端到端实现与验证}。在 Flower 平台完成 20 客户端、6 类混合攻击实验（$n=5$）；结果显示框架在高对抗设置下仍保持 $92.31\% (\pm 0.09\%)$ 精度、$10.21\% (\pm 0.05\%)$ ASR，以及接近 0 的永久误杀率。
\end{enumerate}

**【英文翻译】**
The primary contributions of this paper are:
\begin{enumerate}
    \item \textbf{Proposing a TEE-anchored dynamic admission mechanism for edge clients.} Remote attestation defines the client admission boundary. Variations in gradients, losses, and instruction distributions during training are then transformed into entropy features. By leveraging Kalman filtering to update the $TrustScore$, admission control extends from a one-time static verification to a continuously evolving trust metric.
    \item \textbf{Developing a dual-stream orthogonal reputation evolution mechanism against stealthy attacks.} Client states are decoupled into a historical utility stream (HistPerf) and an instant risk stream (RiskEMA), independently handling long-term contributions and sudden anomalies. A $RawScore$ connects content auditing, state transitions, and subsequent aggregation control, balancing malicious recall with the suppression of permanent false positives.
    \item \textbf{Designing a layered risk gating aggregation strategy tailored for strong Non-IID scenarios.} Guided by a server-side clean reference direction, layer-wise security sensitivities, and dynamic L2 clipping, this approach applies differentiated admission thresholds and survivor weight re-normalization across network layers. It reduces the risk of deep backdoor penetration while preserving valid updates from legitimate long-tail nodes.
    \item \textbf{Implementing and validating the framework end-to-end under mixed attack scenarios.} Experiments involving 20 clients and 6 mixed attack types ($n=5$) were conducted on the Flower platform. Results demonstrate that under high-adversarial settings, the proposed framework maintains an accuracy of $92.31\% (\pm 0.09\%)$ and restricts the ASR to $10.21\% (\pm 0.05\%)$, with the permanent false positive rate approaching zero.
\end{enumerate}

# 第二部分：背景与相关工作 (Section 2: Background and Related Work)

**【中文原文】**
\subsection{联邦学习与边缘计算协同架构}
联邦学习（Federated Learning, FL）在“数据不出本地”的约束下，通过参数协同完成全局模型训练。在边缘计算场景中，端-边-云（Client-Edge-Cloud）的架构模式已被广泛采用：边缘侧负责本地训练并上传更新，中心服务器负责聚合与模型下发。

**【英文翻译】**
\subsection{联邦学习与边缘计算协同架构}
Under the privacy constraint of keeping data local, federated learning (FL) accomplishes global model training through parameter collaboration. In edge computing scenarios, the client-edge-cloud architectural paradigm has been widely adopted, where the edge side undertakes local training and uploads updates, while the central server handles aggregation and model distribution.

**【中文原文】**
在标准的 FL 设置中，全局优化目标为最小化所有客户端数据分布上的经验风险：
\begin{equation}
    \min_{W} \mathcal{L}(W) = \sum_{k=1}^K p_k \mathcal{L}_k(W)
\end{equation}
其中 $p_k = |\mathcal{D}_k| / \sum |\mathcal{D}_j|$ 为数据量占比。在第 $t$ 轮，服务器下发全局模型 $W_{global}^{(t-1)}$，客户端 $k$ 以其为初值在本地数据上执行 $E$ 轮学习率为 $\eta_l$ 的 SGD，得到本地更新：
\begin{equation}
    \Delta W_{k}^{(t)} = W_{k, E}^{(t)} - W_{global}^{(t-1)}, \quad \text{其中 } W_{k, e}^{(t)} = W_{k, e-1}^{(t)} - \eta_l \nabla \mathbb{E}[\ell(W_{k, e-1}^{(t)}; x, y)]
\end{equation}
其中，期望 $\mathbb{E}[\cdot]$ 表示对本地数据集 $\mathcal{D}_k$ 的 mini-batch 采样期望。随后，客户端上传更新量，服务器执行某种形式的参数聚合：$W_{global}^{(t)} = W_{global}^{(t-1)} + \mathrm{Agg}(\{ \Delta W_{k}^{(t)} \}_{k\in\Phi})$。

**【英文翻译】**
In standard FL configurations, the global optimization objective is to minimize the empirical risk across all client data distributions:
\begin{equation}
    \min_{W} \mathcal{L}(W) = \sum_{k=1}^K p_k \mathcal{L}_k(W)
\end{equation}
where $p_k = |\mathcal{D}_k| / \sum |\mathcal{D}_j|$ represents the data volume proportion. During the $t$-th round, the server distributes the global model $W_{global}^{(t-1)}$. Utilizing this as the initial value, client $k$ performs $E$ epochs of SGD with a learning rate $\eta_l$ on its local data to derive the local update:
\begin{equation}
    \Delta W_{k}^{(t)} = W_{k, E}^{(t)} - W_{global}^{(t-1)}, \quad \text{其中 } W_{k, e}^{(t)} = W_{k, e-1}^{(t)} - \eta_l \nabla \mathbb{E}[\ell(W_{k, e-1}^{(t)}; x, y)]
\end{equation}
Here, the expectation $\mathbb{E}[\cdot]$ denotes the mini-batch sampling expectation over the local dataset $\mathcal{D}_k$. Subsequently, clients upload their update quantities, and the server executes a specific form of parameter aggregation: $W_{global}^{(t)} = W_{global}^{(t-1)} + \mathrm{Agg}(\{ \Delta W_{k}^{(t)} \}_{k\in\Phi})$.

**【中文原文】**
但是该架构天然存在通信延迟、设备异构和数据 Non-IID 等问题。为缓解这些挑战，已有研究提出簇式联邦（Clustered FL）\cite{r9_clustered}、自适应剪枝扩展（FedPE）\cite{fedpe} 和拆分式联邦（ParallelSFL）\cite{parallelsfl} 等方法。但随着系统复杂度提升，攻击面也随之扩大，恶意节点也更易潜伏并影响训练过程。

**【英文翻译】**
Nevertheless, this architecture inherently suffers from communication latency, device heterogeneity, and Non-IID data distributions. To alleviate these challenges, existing research has proposed methods such as Clustered FL \cite{r9_clustered}, adaptive model pruning-expanding (FedPE) \cite{fedpe}, and ParallelSFL \cite{parallelsfl}. However, as system complexity increases, the attack surface expands accordingly, enabling malicious nodes to remain stealthy more easily and disrupt the training process.

**【中文原文】**
\subsection{边缘伪装、模型投毒与隐蔽后门攻击}
在开放且缺少强制准入的联邦网络中，服务器难以准确判断客户端身份与更新质量，攻击手段主要分为两类：其一是\textbf{无目标投毒}（Untargeted Poisoning），如 Sign-flipping 与 Gradient Scaling，目标是破坏全局收敛并造成拒绝服务；其二是\textbf{目标后门攻击}（Targeted Backdoor），如标签翻转、干净标签污染和语义后门，通过隐蔽触发器在推理阶段诱导定向误分类。

**【英文翻译】**
\subsection{边缘伪装、模型投毒与隐蔽后门攻击}
Within open federated networks lacking mandatory admission control, the server struggles to accurately ascertain client identities and update quality. Attack vectors predominantly fall into two categories. The first involves \textbf{untargeted poisoning}, such as sign-flipping and gradient scaling, aiming to shatter global convergence and induce denial-of-service. The second category comprises \textbf{targeted backdoor} attacks, including label flipping, clean-label poisoning, and semantic backdoors. These attacks leverage stealthy triggers to induce directed misclassification during the inference phase.

**【中文原文】**
\subsection{现有主动防御防线的机制与不可调和的局限性}
为应对上述威胁，早期防御多依赖几何统计过滤，例如 Krum\cite{blanchard2017krum} 与 Trimmed Mean\cite{yin2018byzantine}。近期的研究进一步引入了时序信任评估，如 FLTrust\cite{cao2021fltrust}、FoolsGold\cite{fung2020foolsgold} 与 RaSA\cite{wang2025rasa}，并在恶意检测\cite{dou2025toward}、可信训练框架\cite{lu2025tmt}、分级保护\cite{wang2024federated} 等方向持续扩展。针对后门与合谋攻击，也已有 FLPurifier\cite{flpurifier}、RoseAgg\cite{roseagg} 和 ShieldFL\cite{shieldfl} 等方案。
但纯软件防御在强 Non-IID 与高权限攻击下仍有明显短板：阈值收紧会抬高误杀率（FPR），阈值放宽又可能放过潜伏攻击；同时，当攻击者控制底层环境时，缺少硬件信任根的软件探针难以形成完整闭环。

**【英文翻译】**
\subsection{现有主动防御防线的机制与不可调和的局限性}
To counter the aforementioned threats, early defense mechanisms heavily relied on geometric statistical filtering, exemplified by Krum \cite{blanchard2017krum} and Trimmed Mean \cite{yin2018byzantine}. More recent investigations have introduced temporal trust evaluations—such as FLTrust \cite{cao2021fltrust}, FoolsGold \cite{fung2020foolsgold}, and RaSA \cite{wang2025rasa}—continuously expanding into domains like malicious detection \cite{dou2025toward}, trustworthy training frameworks \cite{lu2025tmt}, and hierarchical protection \cite{wang2024federated}. For backdoor and collusion attacks, paradigms including FLPurifier \cite{flpurifier}, RoseAgg \cite{roseagg}, and ShieldFL \cite{shieldfl} have also been developed. 
Despite these advancements, purely software-based defenses exhibit conspicuous vulnerabilities under strong Non-IID conditions and high-privilege attacks. Tightening the threshold elevates the false positive rate (FPR), whereas relaxing it risks overlooking stealthy attacks. Furthermore, if adversaries compromise the underlying execution environment, software probes lacking hardware trust roots struggle to form a complete, secure closed loop.

**【中文原文】**
\subsection{联邦环境下的可信硬件信任根 (TEE)}
为补齐物理可信的缺口，研究开始引入 Intel SGX、ARM TrustZone 等可信执行环境（TEE）。TEE 通过隔离执行与受保护内存保证关键代码和密钥材料的完整性，即便宿主操作系统被攻陷，攻击者也难以直接篡改证明流程\cite{liao2024verifiable,zhang2025rppfl}。现有的工作表明，TEE 在训练完整性\cite{r1_tee_integrity}、威胁缓解\cite{r5_tee_mitigating} 和工业 IoT 信任共享\cite{r12_iot_tee} 中具备现实价值，其在 SGX 环境下的联邦扩展与效率优化也得到验证\cite{xu2021distributed,yan2024efficient}。
本文在此基础上构建软硬件协同防御体系。与仅做静态加密或单维异常评测的方法不同，本文将硬件远程证明（Remote Attestation）与双流信誉演化进行时序耦合：云端负责参数审查，边缘侧 TMAA 提供可信证据与运行时监测，实现“强制准入 + 动态熔断”的联动防护。

**【英文翻译】**
\subsection{联邦环境下的可信硬件信任根 (TEE)}
To bridge the gap in physical trustworthiness, researchers have begun integrating trusted execution environments (TEEs) such as Intel SGX and ARM TrustZone. TEEs ensure the integrity of critical code and key materials through isolated execution and protected memory. Consequently, even if the host operating system is breached, attackers face immense difficulty in directly tampering with the attestation process \cite{liao2024verifiable,zhang2025rppfl}. Existing literature demonstrates that TEEs hold practical value in maintaining training integrity \cite{r1_tee_integrity}, mitigating threats \cite{r5_tee_mitigating}, and enabling trust sharing in industrial IoT \cite{r12_iot_tee}. Their federated expansion and efficiency optimization under SGX environments have also been empirically validated \cite{xu2021distributed,yan2024efficient}.
Building upon this foundation, our work constructs a hardware-software synergistic defense architecture. In contrast to methods relying solely on static encryption or single-dimensional anomaly assessment, we temporally couple hardware remote attestation with dual-stream reputation evolution. Specifically, the cloud assumes responsibility for parameter auditing, while the edge-side TMAA provides trustworthy evidence and runtime monitoring, thereby achieving a coordinated defense mechanism of "mandatory admission plus dynamic circuit breaking."

# 第三部分：系统模型与问题定义 (Section 3: System Model and Problem Definition)

**【中文原文】**
\subsection{端边云协同架构与系统流转建模}
本文考虑一个典型的端-边-云（Client-Edge-Cloud）异构通信环境（见图~\ref{fig:system_arch}）。系统由中心\textbf{聚合服务器（Server, $\mathcal{S}$）}与 $K$ 个边缘客户端组成，记为 $\mathcal{C}=\{c_1, c_2, \dots, c_K\}$。客户端可能动态上下线，且部分节点可能被攻击者控制。

**【英文翻译】**
\subsection{端边云协同架构与系统流转建模}
This paper considers a typical client-edge-cloud heterogeneous communication environment (see Figure~\ref{fig:system_arch}). The system consists of a central \textbf{aggregation server (Server, $\mathcal{S}$)} and $K$ edge clients, denoted as $\mathcal{C}=\{c_1, c_2, \dots, c_K\}$. Clients may dynamically join or leave the network, and a fraction of these nodes might be compromised by attackers.

\begin{figure}[htbp!]
    \centering
    \includegraphics[width=0.90\textwidth]{fig1_system_arch.pdf}
    \caption{联邦计算网络交互：基于 TEE 锚点加密的端边云协同物理架构图}
    \label{fig:system_arch}
\end{figure}

**【中文原文】**
基于上述网络交互拓扑，本文提出的信任流驱动可信联邦框架在端云之间构建了一条完整的信任传递与评估链路。系统的整体工作流程与主要物理实体模块的相互关系定义如下：
\begin{enumerate}
    \item \textbf{边缘客户端侧（可信执行与特征提取）}：每个接入的客户端需配备可信执行环境（TEE）及部署其内的可信管理代理（TMAA）。在本地训练阶段，TMAA 不仅负责在训练前生成远程证明报告（Attestation Quote）以静态验证执行环境的完整性，还会持续监测训练过程中的关键行为特征序列（如梯度方向变化、损失值波动等）。随后，利用信息熵和卡尔曼滤波进行初步的动态信任评估，连同模型更新参数一并上传至云端。
    \item \textbf{中心服务器侧（审查、演化与聚合控制）}：服务器作为全局协调者，接收到客户端的更新及信任证明后，执行基于信任流的三阶联动防御。首先进行\textbf{内容审查}，提取纯净参考方向并利用余弦相似度计算高维更新质量；其次进入\textbf{双流状态演化}，利用 Beta 贝叶斯推断建立历史效用流以评估长期贡献，并结合多维最大值探针更新瞬时风险流以识别突发异常；最后执行\textbf{分层鲁棒聚合}，根据不同网络层的安全敏感度进行差异化门控裁剪与幸存者权重重归一化，得到全局安全更新并下发。
\end{enumerate}
通过上述端与云实体模块的协同交互，系统实现了“硬件门禁准入 $\to$ 运行特征监测 $\to$ 信任状态演化 $\to$ 风险门控聚合”的全生命周期物理与逻辑流转闭环。

**【英文翻译】**
Based on the aforementioned network interaction topology, the proposed trust-flow-driven trusted federated framework establishes a comprehensive trust transmission and evaluation pipeline between the edge and the cloud. The overall operational workflow, along with the relationships among principal physical entity modules, is defined as follows:
\begin{enumerate}
    \item \textbf{Edge Client Side (Trusted Execution and Feature Extraction)}: Every participating client must be equipped with a trusted execution environment (TEE), wherein a trusted management agent (TMAA) is deployed. During the local training phase, the TMAA is tasked not only with generating an Attestation Quote prior to training to statically verify the integrity of the execution environment, but also with continuously monitoring sequences of critical behavioral features throughout the training process (e.g., shifts in gradient directions and loss value fluctuations). Subsequently, it employs information entropy and Kalman filtering to conduct a preliminary dynamic trust assessment, transmitting this evaluation alongside the model parameter updates to the cloud.
    \item \textbf{Central Server Side (Auditing, Evolution, and Aggregation Control)}: Acting as the global coordinator, the server receives the clients' updates and trust credentials, subsequently executing a three-stage coordinated defense driven by the trust flow. Initially, it conducts \textbf{content auditing} by extracting a pure reference direction and computing the high-dimensional update quality via cosine similarity. Following this, the system proceeds to \textbf{dual-stream state evolution}, employing Beta Bayesian inference to establish a historical utility stream for evaluating long-term contributions, while integrating multi-dimensional max-value probes to update an instant risk stream for detecting sudden anomalies. Finally, it enforces \textbf{layered robust aggregation}, applying differentiated gated clipping and survivor weight re-normalization based on the security sensitivities of distinct network layers to derive and distribute the global secure update.
\end{enumerate}
Through this synergistic interaction between edge and cloud entity modules, the system successfully realizes a full-lifecycle physical and logical closed loop, progressing seamlessly from "hardware admission control" and "runtime feature monitoring," to "trust state evolution," and ultimately "risk-gated aggregation."

**【中文原文】**
\subsection{复合型威胁假设与强信任底座边界 (Threat Model)}
为清晰界定攻防能力边界，本文采用如下威胁模型（见图~\ref{fig:threat_model}）：
\begin{itemize}
    \item \textbf{硬件隔离边界（信任根）}：在标准安全假设下（不考虑微架构侧信道与物理探针等高级攻击\cite{zhang2025rppfl}），即使宿主操作系统被攻陷，TEE（如 TrustZone/SGX）仍可保证关键执行与证明流程的完整性。
    \item \textbf{诚实但好奇 （Honest-but-curious）}：服务器按协议执行双流评分和分层聚合流程，但可能尝试额外推断客户端隐私信息。
    \item \textbf{内部恶意客户端（Internal Attackers/Poisoners）}：攻击者可持有合法接入身份，并在本地执行标签篡改、样本污染、符号翻转、梯度缩放等操作。本文假设恶意占比上限为 $<50\%$；主实验采用 30\% 作为典型高风险设置，并额外给出 50\% 边界压力测试。
\end{itemize}

**【英文翻译】**
\subsection{复合型威胁假设与强信任底座边界 (Threat Model)}
To clearly delineate the boundaries of offensive and defensive capabilities, this paper adopts the following threat model (see Figure~\ref{fig:threat_model}):
\begin{itemize}
    \item \textbf{Hardware Isolation Boundary (Root of Trust)}: Under standard security assumptions (excluding advanced exploits such as microarchitectural side-channels and physical probing \cite{zhang2025rppfl}), TEEs (e.g., TrustZone or SGX) can guarantee the integrity of critical execution and attestation processes even if the host operating system is completely compromised.
    \item \textbf{Honest-but-Curious Server}: The server faithfully executes the dual-stream scoring and layered aggregation protocols but may attempt to additionally infer private client information.
    \item \textbf{Internal Malicious Clients (Internal Attackers/Poisoners)}: Adversaries possess legitimate admission identities and can execute local operations such as label tampering, sample poisoning, sign flipping, and gradient scaling. This study assumes an upper bound on the malicious proportion of $<50\%$; the main experiments utilize 30\% to represent a typical high-risk setting, while additionally providing a 50\% boundary stress test.
\end{itemize}

\begin{figure}[htbp!]
    \centering
    \includegraphics[width=0.88\textwidth]{fig2_threat_model.pdf}
    \caption{边缘广域网络下的安全渗透与多维复合型投毒威胁模型示意图}
    \label{fig:threat_model}
\end{figure}

**【中文原文】**
\subsection{安全架构核心防护优化导向 (Design Goals)}
针对高异构数据与高比例恶意参与者，本文框架的设计目标如下：
\begin{enumerate}
    \item \textbf{高防御效能与鲁棒收敛保障}：在面对多类投毒与后门攻击时，系统需具备精准的恶意节点识别能力（即高 TPR 与低 ASR），同时确保全局主任务模型的高可用性与稳定收敛。
    \item \textbf{异构长尾节点的高包容度}：有效克服 Non-IID 数据分布带来的特征偏离干扰，避免将携带长尾数据的诚实节点错误剔除，保障系统的假阳性率（FPR）趋近于零。
    \item \textbf{轻量级开销与边缘适配性}：在不引入全量密码学（如全同态加密）计算负担的前提下，构建高效的可信防护机制，确保系统算力与通信开销严格可适应边缘异构设备的资源瓶颈。
\end{enumerate}

**【英文翻译】**
\subsection{安全架构核心防护优化导向 (Design Goals)}
Targeting scenarios with highly heterogeneous data and significant proportions of malicious participants, the design objectives of our framework are outlined below:
\begin{enumerate}
    \item \textbf{High Defensive Efficacy and Robust Convergence Guarantee}: When confronted with diverse poisoning and backdoor attacks, the system must exhibit precise malicious node identification capabilities (i.e., high TPR and low ASR), while simultaneously ensuring the high availability and stable convergence of the global main-task model.
    \item \textbf{High Tolerance for Heterogeneous Long-Tail Nodes}: The framework aims to effectively overcome the feature deviation interference induced by Non-IID data distributions. This prevents the erroneous elimination of honest nodes carrying long-tail data, thereby ensuring that the system's false positive rate (FPR) approaches zero.
    \item \textbf{Lightweight Overhead and Edge Adaptability}: Without incurring the profound computational burdens of full-scale cryptography (e.g., fully homomorphic encryption), the architecture seeks to construct an efficient, trusted protection mechanism. This ensures that computational and communication overheads remain strictly compatible with the resource bottlenecks of heterogeneous edge devices.
\end{enumerate}

# 第四部分：本文方法：信任流驱动的可信联邦框架 (Section 4: Proposed Method)

**【中文原文】**
针对上述威胁模型，本文提出“信任流驱动的可信联邦学习”框架（见图~\ref{fig:framework}）。从联邦学习的执行次序看，该框架先在客户端侧完成可信准入和运行监测，再在服务器侧完成当轮内容审查与跨轮信誉演化，最后进入聚合阶段的分层安全控制。由此，每一轮训练被划分为五个阶段：训练前准入、内容审查、状态演化、分层聚合和全局下发；若进一步抽象，可对应为“客户端准入与监测、服务器审查与演化、聚合安全保障”三个层次。

**【英文翻译】**
Addressing the aforementioned threat model, this paper proposes a "trust-flow-driven trusted federated learning" framework (see Figure~\ref{fig:framework}). Following the execution sequence of federated learning, this framework first conducts trusted admission and runtime monitoring on the client side, then performs current-round content auditing and cross-round reputation evolution on the server side, and finally executes layered security control during the aggregation phase. Consequently, each training round is systematically divided into five stages: pre-training admission, content auditing, state evolution, layered aggregation, and global distribution. At a higher level of abstraction, this architecture corresponds to three defensive tiers: "client admission and monitoring," "server auditing and evolution," and "aggregation security assurance."

**【中文原文】**
这种“总-分”结构的核心在于信任状态的连续传递。阶段一输出 $，回答客户端是否具备可信接入和可信执行基础；阶段二输出 $，判断本轮上传更新是否偏离纯净参考和群体协作方向；阶段三将当轮信号沉淀为 $ 与 $，区分长期低贡献和短时高风险；阶段四再把三类信号融合为 $，并按网络层执行差异化聚合。不同于单点防御，每阶段产生的数据会在后续阶段继续发挥约束作用，持续更新\textbf{信任流（Trust Flow）}并形成闭环控制。

**【英文翻译】**
The core of this "macro-to-micro" structure lies in the continuous transmission of trust states. Phase one outputs the $, verifying whether the client possesses a foundation for trusted admission and execution. Phase two generates the $, assessing whether the uploaded update in the current round deviates from the pure reference and collective collaboration direction. Phase three consolidates the current-round signals into $ and $, delineating long-term low contributions from short-term high risks. Phase four subsequently fuses these three categories of signals into a $, performing differentiated aggregation according to the specific network layer. Unlike isolated point defenses, the data generated in each phase actively constrains subsequent phases, continuously updating the \textbf{Trust Flow} and forging a closed-loop control mechanism.

\begin{figure}[htbp]
    \centering
    \includegraphics[width=\textwidth]{fig3_arch.pdf}
    \caption{信任流驱动的可信联邦学习五阶段防御闭环架构总览}
    \label{fig:framework}
\end{figure}

**【中文原文】**
为便于后续推导，表~\ref{tab:notations} 给出核心符号定义。

**【英文翻译】**
To facilitate subsequent derivations, Table~\ref{tab:notations} presents the definitions of core symbols.

\begin{table}[htbp]
    \centering
    \caption{核心系统参数与信任流符号定义}
    \label{tab:notations}
    \renewcommand{\arraystretch}{1.25}
    \setlength{\tabcolsep}{3pt}
    \begin{tabular*}{\textwidth}{@{\extracolsep{\fill}} >{\raggedright\arraybackslash}p{2.8cm} >{\raggedright\arraybackslash}p{4.5cm} >{\raggedright\arraybackslash}p{2.2cm} >{\raggedright\arraybackslash}p{4.5cm}}
        \toprule
        \textbf{符号} & \textbf{定义描述} & \textbf{符号} & \textbf{定义描述} \
        \midrule
        {global}^{(t)}$ & 第 $ 轮的全局模型权重 & $\mathcal{A}$ & 本轮具备有效聚合资格的活跃节点集合 \
        $\Delta W_k$ & 客户端 $ 提交的模型梯度/参数更新 & $\Phi^{(l)}$ & 第 $ 层的有效安全幸存者子集 \
        $ & TEE 硬件锚定的准入基础信任分 & $ & 历史效用流累积状态 ( \in [0, 1]$)\
        $ & 双参比下的当轮内容质量得分 & $ & 瞬时风险流衰减状态 ( \in [0, 1]$)\
        $ & 融合三维得分并施加风险折扣的最终权限分 & {attest,k}$ & 硬件远程证明 (Attestation) 验证通过标志 \
        {root}$ & 服务器提取的纯净指导锚点方向 & $ & 客户端 $ 的物理资源运行时异常分数 \
        \bottomrule
    \end{tabular*}
    \renewcommand{\arraystretch}{1.0}
\end{table}

**【中文原文】**
\subsection{硬件准入与动态信任评估}
客户端的准入机制不应局限于一次性的身份校验，而需建立一套反映本地训练持续可信度的追踪体系。为此，本研究将初始可信度解耦为“静态准入”与“动态评估”双层架构：前者依赖底层硬件判断执行环境的合法性；后者则利用信息理论学习（Information Theoretic Learning, ITL）的前沿范式\cite{chen2017maximum}，将训练过程中的瞬态行为波动转化为动态观测信号，借由滤波机制输出可持续传递的 $。

**【英文翻译】**
\subsection{硬件准入与动态信任评估}
Client admission mechanisms should not be confined to one-time identity verification; rather, they require a tracking system capable of reflecting the continuous trustworthiness of local training. To this end, this study decouples the initial credibility into a two-tier architecture comprising "static admission" and "dynamic evaluation." The former relies on the underlying hardware to determine the legitimacy of the execution environment. The latter leverages the cutting-edge paradigm of Information Theoretic Learning (ITL) \cite{chen2017maximum}, transforming transient behavioral fluctuations during the training process into dynamic observation signals. Through a filtering mechanism, this tier outputs a sustainably transmissible $.

**【中文原文】**
\begin{enumerate}
    \item \textbf{硬件静态门禁（Static Admission）}：在联邦计算初始化阶段，参与节点必须调用其内部隔离的硬件密钥（DUK），向中心服务器发起包含平台配置寄存器（PCRs）链值的远程证明（Attestation Quote）。服务器端通过校验内存代码段与运行态签名，对通过验证的节点授予初始通信权限（{attest,k}=1$）。
    \item \textbf{特征序列提取与熵分析（Entropy Analysis）}：在分布式系统的抗投毒信任评估框架中\cite{li2026multidimensional}，单一的静态测量难以捕获复杂的运行期突变。因此，客户端 TEE 内部被配置为持续监测训练周期的关键特征序列 $\mathcal{X}_k = \{ \Delta \text{grad}, \Delta \text{loss}, \text{instr\_dist} \}$。对该序列的信息熵 (\mathcal{X}_k)$ 进行量化计算：
          \begin{equation}
              H(\mathcal{X}_k) = -\sum p(x_i) \log p(x_i)
          \end{equation}
          序列呈现高熵值往往揭示了更强的系统运行不确定性，这在物理意义上通常对应着被后门植入控制、梯度方向剧烈扰动或是底层的指令分布异常。
    \item \textbf{信息理论驱动的动态信任演化（Kalman-based Evolution）}：为防范异常突变对信任状态的污染，本框架构建了一种熵驱动的自适应协方差映射机制。系统摒弃了恒定常数的先验假设，将动态捕捉到的信息熵物理映射为卡尔曼观测方程中的测量噪声协方差矩阵  = f(H(\mathcal{X}_k))$。在经典的“预测-更新”递推循环中：
          \begin{itemize}
              \item \textbf{预测阶段}：依托上一轮次后验分布，外推当前时刻的信任先验期望 $\hat{T}_k^-$。
              \item \textbf{更新阶段}：引入本轮瞬时行为特征完成测量更新，进而解析出后验信任估计值 $\hat{T}_k$ 及与之对应的状态误差协方差矩阵 $。
          \end{itemize}
\end{enumerate}

**【英文翻译】**
\begin{enumerate}
    \item \textbf{Static Hardware Admission Gate}: During the initialization phase of federated computing, participating nodes must invoke their internally isolated device-unique keys (DUK) to initiate a Remote Attestation Quote. This quote encompasses the chain values of the platform configuration registers (PCRs). The server subsequently grants initial communication privileges ({attest,k}=1$) to nodes that successfully pass verification, by cross-referencing memory code segments and runtime signatures.
    \item \textbf{Feature Sequence Extraction and Entropy Analysis}: Within the anti-poisoning trust evaluation framework of distributed systems \cite{li2026multidimensional}, solitary static measurements consistently fall short in capturing intricate runtime mutations. Therefore, the internal client TEE is configured to continuously monitor sequences of vital behavioral features throughout the training cycle, denoted as $\mathcal{X}_k = \{ \Delta \text{grad}, \Delta \text{loss}, \text{instr\_dist} \}$. The information entropy of this sequence, (\mathcal{X}_k)$, is quantitatively evaluated as follows:
          \begin{equation}
              H(\mathcal{X}_k) = -\sum p(x_i) \log p(x_i)
          \end{equation}
          A sequence exhibiting high entropy typically unveils amplified systemic operational uncertainty. In a physical context, this conventionally corresponds to malicious backdoor takeover, violent perturbations in gradient directions, or profound anomalies in underlying instruction distributions.
    \item \textbf{Information-Theory-Driven Dynamic Trust Evolution (Kalman-based Evolution)}: To shield the trust state against corruption from anomalous spikes, the framework incorporates an entropy-driven adaptive covariance mapping mechanism. The system discards the prior assumption of invariable constants, physically mapping the dynamically captured information entropy to the measurement noise covariance matrix in the Kalman observation equation:  = f(H(\mathcal{X}_k))$. In the classical "predict-update" recursive loop:
          \begin{itemize}
              \item \textbf{Prediction Stage}: Relying on the posterior distribution from the preceding round, the system extrapolates the prior trust expectation $\hat{T}_k^-$ for the current moment.
              \item \textbf{Update Stage}: The current round\'s transient behavioral features are integrated to fulfill the measurement update. Consequently, the framework derives the posterior trust estimate $\hat{T}_k$, along with its corresponding state error covariance matrix $.
          \end{itemize}
\end{enumerate}

**【中文原文】**
在此基础上，结合异常序列的高熵惩罚特性，系统引入核心状态演化法则：
\begin{align}
    \hat{T}_k^{(t)} & = \hat{T}_k^{(t-1)} + K_k^{(t)} (Z_k^{(t)} - \hat{T}_k^{(t-1)}) \
    R_k^{(t)}       & = \exp(\lambda \cdot H(\mathcal{X}_k^{(t)}))
\end{align}
方程中 ^{(t)}$ 映射了节点实时的基线观测效用。当客户端行为发生高风险跳变（即高熵）时，指数级放大的 ^{(t)}$ 会促使卡尔曼增益 ^{(t)}$ 迅速衰减。这一机制促使滤波器自动抑制高风险异常瞬时观测值的吸收，以此维持信任后验估计的平稳抗毁性。

**【英文翻译】**
Building upon this foundation, and integrating the high-entropy penalty trait inherent to anomalous sequences, the system introduces the core state evolution law:
\begin{align}
    \hat{T}_k^{(t)} & = \hat{T}_k^{(t-1)} + K_k^{(t)} (Z_k^{(t)} - \hat{T}_k^{(t-1)}) \
    R_k^{(t)}       & = \exp(\lambda \cdot H(\mathcal{X}_k^{(t)}))
\end{align}
In these equations, ^{(t)}$ reflects the real-time baseline observed utility of the node. When a client\'s behavior experiences a high-risk surge (i.e., high entropy), the exponentially amplified ^{(t)}$ forces the Kalman gain ^{(t)}$ to decay precipitously. This mechanism inherently compels the filter to autonomously suppress the absorption of high-risk, anomalous instantaneous observations, thereby sustaining the steady resilience of the posterior trust estimation.

**【中文原文】**
进一步地，根据贝叶斯滤波的数学本质，滤波器迭代输出的协方差矩阵 $ 天然且客观地表征了该节点动态信任估计值的“置信度边界”——$ 值越小，表明当前滤波器的测量噪声得到有效压制，信誉评分的可靠程度越高。借此，阶段一不再输出粗粒度的二分类裁决，而是将卡尔曼滤波产生的期望均值与不确定性进行联合演化，形成具备时序韧性的门禁权限因子  = \hat{T}_k^{(t)} \cdot (1 / (1 + P_k^{(t)}))$。

**【英文翻译】**
Furthermore, following the mathematical essence of Bayesian filtering, the covariance matrix $ iteratively yielded by the filter naturally and objectively characterizes the "confidence boundary" of the node\'s dynamic trust estimation. A smaller $ indicates that the current filter\'s measurement noise has been effectively suppressed, signifying a higher degree of reliability in the reputation score. Consequently, phase one transcends coarse-grained binary verdicts. Instead, it concurrently evolves the expected mean and the uncertainty derived from the Kalman filter, forging an access privilege factor endowed with temporal resilience:  = \hat{T}_k^{(t)} \cdot (1 / (1 + P_k^{(t)}))$.

**【中文原文】**
\subsection{参考方向构建与一致性审查}
仅依赖客户端之间的余弦相似度容易被合谋攻击误导，为此，本文引入\textbf{优先纯净参考（Vanilla Reference Prioritization）}。当服务器持有少量隔离验证集（Pure Clean Set）时，先计算 {root\_clean}$ 作为参考方向；若该方向不可用，则由高信任、低风险客户端更新构造退化参考 {ref}$。其权重定义为：
\begin{equation}
    \omega_{k}^{ref} = TrustScore_{k} \cdot (1 - RiskEMA_{k}^{prev})^{2}.
\end{equation}
最终参考方向 {root}$ 为：
\begin{equation}
    g_{root}=
    \begin{cases}
        g_{root\_clean},                                                      & \text{若服务器验证集方向可用}, \
        \sum_{k} \frac{\omega_{k}^{ref}}{\sum_j \omega_{j}^{ref}} \Delta W_k, & \text{否则}.
    \end{cases}
\end{equation}

**【英文翻译】**
\subsection{参考方向构建与一致性审查}
Relying exclusively on cosine similarity among clients is heavily susceptible to collusion attacks. To overcome this limitation, this paper introduces \textbf{Vanilla Reference Prioritization}. When the server maintains a small, isolated validation set (Pure Clean Set), it first computes {root\_clean}$ to serve as the reference direction. If this direction is unavailable, a degraded reference {ref}$ is constructed using updates from high-trust, low-risk clients. The corresponding weight is defined as follows:
\begin{equation}
    \omega_{k}^{ref} = TrustScore_{k} \cdot (1 - RiskEMA_{k}^{prev})^{2}.
\end{equation}
Ultimately, the reference direction {root}$ is formulated as:
\begin{equation}
    g_{root}=
    \begin{cases}
        g_{root\_clean},                                                      & \text{若服务器验证集方向可用}, \
        \sum_{k} \frac{\omega_{k}^{ref}}{\sum_j \omega_{j}^{ref}} \Delta W_k, & \text{否则}.
    \end{cases}
\end{equation}

**【中文原文】**
在得到 {root}$ 后，服务器对每个客户端更新 $\Delta W_k$ 计算内容质量分。该分数同时考虑全局贡献（与参考方向一致性）和群体一致性（与其他高信誉客户端一致程度）：
\begin{align}
    S_{contrib,k}    & = \max\left(0,\ \alpha_{1} + \alpha_{2} \cdot \cos(\Delta W_{k}, g_{root})\right),                                                                                             \
    S_{consist,k}    & = \frac{\sum_{j\neq k} TrustScore_{j} \cdot \max\left(0,\ \alpha_{1} + \alpha_{2} \cdot \cos(\Delta W_{k}, \Delta W_{j})\right)}{\sum_{j\neq k} TrustScore_{j} + \varepsilon}, \
    ContentScore_{k} & = \frac{(1 + \beta_{fusion}^{2}) \cdot S_{consist,k} \cdot S_{contrib,k}}{\beta_{fusion}^{2}\cdot S_{consist,k} + S_{contrib,k} + \varepsilon}.
\end{align}
其中，$\alpha_1+\alpha_2=1.0$ 用于调节余弦映射区间；$\beta_{fusion}>1.0$（默认 $\beta_{fusion}=2.0$）表示适当提高“与纯净方向一致”的权重，以增强对合谋偏移的抑制能力。$ 只描述本轮更新的内容质量，并不直接等同于永久信誉。对于强 Non-IID 场景中的长尾合法节点，单轮低分可能来自数据偏斜而非攻击行为，因此该分数会继续进入阶段三的跨轮状态演化，由历史效用流和瞬时风险流共同决定后续处置。

**【英文翻译】**
Upon establishing {root}$, the server calculates the content quality score for each client\'s update $\Delta W_k$. This score concurrently evaluates the global contribution (alignment with the reference direction) and group consistency (the degree of alignment with other highly reputable clients):
\begin{align}
    S_{contrib,k}    & = \max\left(0,\ \alpha_{1} + \alpha_{2} \cdot \cos(\Delta W_{k}, g_{root})\right),                                                                                             \
    S_{consist,k}    & = \frac{\sum_{j\neq k} TrustScore_{j} \cdot \max\left(0,\ \alpha_{1} + \alpha_{2} \cdot \cos(\Delta W_{k}, \Delta W_{j})\right)}{\sum_{j\neq k} TrustScore_{j} + \varepsilon}, \
    ContentScore_{k} & = \frac{(1 + \beta_{fusion}^{2}) \cdot S_{consist,k} \cdot S_{contrib,k}}{\beta_{fusion}^{2}\cdot S_{consist,k} + S_{contrib,k} + \varepsilon}.
\end{align}
Here, $\alpha_1+\alpha_2=1.0$ is utilized to modulate the cosine mapping interval. The parameter $\beta_{fusion}>1.0$ (defaulting to $\beta_{fusion}=2.0$) dictates a proportional amplification of the "consistency with the pure direction" weight, strategically reinforcing the system\'s capacity to suppress collusive drifts. The variable $ solely describes the content quality of the current round\'s update and does not directly equate to permanent reputation. For legitimate long-tail nodes in stark Non-IID scenarios, a low score in a single round may originate from data skew rather than malicious exploits. Consequently, this score proceeds into phase three for cross-round state evolution, where the historical utility stream and instant risk stream collaboratively dictate subsequent disciplinary actions.


\begin{algorithm}[htbp]
    \caption{基于 TEE 硬件锚点与纯净参考的准入与内容审查}
    \label{alg:phase12}
    \begin{algorithmic}[1]
        \REQUIRE 客户端集合 $\mathcal{C}$，本轮收到的参数更新 $\{\Delta W_k\}_{k\in\mathcal{C}}$，上轮状态 ^{(t-1)}$
        \ENSURE $, $, 有效参考基准 {root}$
        \STATE \textbf{第一阶段：硬件锚定与动态信任度量}
        \FOR{每个客户端  \in \mathcal{C}$}
        \IF{{attest,k} == 0$ (TEE 远程证明失败)}
        \STATE 拒绝接入： \leftarrow 0$，并跳过本轮
        \ELSE
        \STATE \textit{TEE 内部}: 记录行为序列 $\mathcal{X}_k = \{ \Delta \text{grad}, \Delta \text{loss}, \text{instr\_dist} \}$
        \STATE 计算信息熵  \leftarrow -\sum p(x_i) \log p(x_i)$
        \STATE 将熵映射为测量噪声  \leftarrow \exp(\lambda \cdot H_k)$
        \STATE \textit{卡尔曼滤波更新}:
        \STATE 信任估计 $\hat{T}_k$, 协方差  \leftarrow \mathrm{KalmanFilter}(H_k, \text{前序状态})$
        \STATE 门禁信任分  \leftarrow \hat{T}_k \cdot \frac{1}{1 + P_k}$
        \ENDIF
        \ENDFOR
        \STATE \textbf{第二阶段：参考方向构建与协同一致性审查}
        \IF{具备服务器纯净验证集数据}
        \STATE 提取真实指导梯度 {root} \leftarrow g_{root\_clean}$
        \ELSE
        \STATE 计算非线性权重 $\omega_k^{ref} \leftarrow TrustScore_k \cdot (1 - RiskEMA_k^{(t-1)})^2$
        \STATE 生成降级纯净锚点 {root} \leftarrow \sum_k (\omega_k^{ref} \Delta W_k) / \sum_j \omega_j^{ref}$
        \ENDIF
        \FOR{通过准入的活跃客户端 $}
        \STATE 全局贡献分 {contrib,k} \leftarrow \max(0, \alpha_1 + \alpha_2 \cos(\Delta W_k, g_{root}))$
        \STATE 群体协作分 {consist,k} \leftarrow \frac{\sum_{j \neq k} TrustScore_j \max(0, \alpha_1 + \alpha_2 \cos(\Delta W_k, \Delta W_j))}{\sum_{j \neq k} TrustScore_j + \varepsilon}$
        \STATE 调和内容分  \leftarrow \frac{(1+\beta_{fusion}^2)S_{consist,k} S_{contrib,k}}{\beta_{fusion}^2 S_{consist,k} + S_{contrib,k} + \varepsilon}$
        \ENDFOR
        \RETURN $\{TrustScore_k, ContentScore_k, g_{root}\}$
    \end{algorithmic}
\end{algorithm}

**【中文原文】**
\subsection{历史效用与瞬时风险的双流演化}
在强 Non-IID（非独立同分布）边缘计算场景中，传统“低分即淘汰”的策略往往混淆了“数据长尾性导致的低效用”与“恶意投毒导致的高风险”，容易引发严重的误杀（FPR）。为破解这一困境，本研究构建二维正交解耦空间，将客户端的状态演化拆分为两个相互独立但在决策阶段汇合的时序流：用于长期能力评估的\textbf{历史效用流（$）}，以及用于捕捉突发异常的\textbf{瞬时风险流（$）}。前者解决“是否长期有贡献”，后者解决“本轮是否存在安全风险”。两类信号不在同一轴上互相抵消，从而缓解传统单维评分体系中误检与漏检的内在冲突。

**【英文翻译】**
\subsection{历史效用与瞬时风险的双流演化}
In edge computing scenarios characterized by strong Non-IID (non-independent and identically distributed) data, the conventional "low-score equals elimination" strategy frequently conflates "low utility induced by data long-tailness" with "high risk caused by malicious poisoning," leading to severe false positive rates (FPR). To disentangle this dilemma, this study constructs a two-dimensional orthogonal decoupling space. The state evolution of clients is segregated into two mutually independent temporal streams that converge during the decision-making phase: a \textbf{historical utility stream ($)} dedicated to evaluating long-term capability, and an \textbf{instant risk stream ($)} tailored for capturing sudden anomalies. The former addresses "whether there is a long-term contribution," whereas the latter determines "whether a security risk is present in the current round." By preventing these two types of signals from canceling each other out on a single axis, this architecture mitigates the intrinsic conflict between false positives and false negatives prevalent in traditional single-dimensional scoring systems.

**【中文原文】**
\textbf{(1) 历史效用流（基于贝叶斯后验推断）}
该支流对节点的持续贡献进行长期评估。在此，本研究引入贝叶斯推断框架（Beta 信誉系统），将客户端 $ 提供高质量梯度的概率建模为 Beta 分布 $\text{Beta}(\alpha_k, \beta_k)$。假设其初始状态为无信息先验 $\text{Beta}(1,1)$，其中 $\alpha_k$ 记录其累积的良性表现，$\beta_k$ 则映射其低质量行为。在联邦学习的每一轮次中，系统基于当轮内容得分 $ 提取正向增益证据 {k}^{good}$ 与负向衰减证据 {k}^{bad}$，并按后验更新方式累积历史证据：
\begin{align}
    r_{k}^{good}     & = \mathrm{clip}\left(\frac{ContentScore_{k} - \mu_{content}}{\sigma_{content} + \varepsilon}, 0, 1\right), \
    r_{k}^{bad}      & = 1 - r_{k}^{good},                                                                                        \
    \alpha_{k}^{(t)} & = \lambda_h \cdot \alpha_{k}^{(t-1)} + r_{k}^{good},                                                       \
    \beta_{k}^{(t)}  & = \lambda_h \cdot \beta_{k}^{(t-1)} + r_{k}^{bad}.
\end{align}
在此体系下，参数 $\lambda_h \in (0,1]$ 作为历史衰减因子，使信誉评估能够适应边缘节点的设备环境漂移，并限制攻击者通过前期长时间伪装累积过高信誉。客户端的长期历史效用值最终取为该后验分布的数学期望：
\begin{equation}
    HistPerf_{k}^{(t)} = \frac{\alpha_{k}^{(t)}}{\alpha_{k}^{(t)} + \beta_{k}^{(t)} + \varepsilon}
\end{equation}
当某节点的 $ 偏低时，仅意味着其近期未能提供充足的正向贡献。系统将对其执行临时软隔离（Soft-Isolation），暂停其本轮聚合权重，但不作永久移除处理。这样可以保留长尾合法节点后续重新贡献真实数据的机会。

**【英文翻译】**
\textbf{(1) Historical Utility Stream (Based on Bayesian Posterior Inference)}
This tributary undertakes the long-term evaluation of a node\'s sustained contributions. Here, the research introduces a Bayesian inference framework (the Beta reputation system), modeling the probability of client $ providing high-quality gradients as a Beta distribution, $\text{Beta}(\alpha_k, \beta_k)$. Assuming an initial state of an uninformative prior $\text{Beta}(1,1)$, $\alpha_k$ records the accumulated benign performance, while $\beta_k$ maps low-quality behavior. In each round of federated learning, the system extracts positive gain evidence {k}^{good}$ and negative decay evidence {k}^{bad}$ based on the current round\'s content score $, subsequently accumulating historical evidence via posterior updating:
\begin{align}
    r_{k}^{good}     & = \mathrm{clip}\left(\frac{ContentScore_{k} - \mu_{content}}{\sigma_{content} + \varepsilon}, 0, 1\right), \
    r_{k}^{bad}      & = 1 - r_{k}^{good},                                                                                        \
    \alpha_{k}^{(t)} & = \lambda_h \cdot \alpha_{k}^{(t-1)} + r_{k}^{good},                                                       \
    \beta_{k}^{(t)}  & = \lambda_h \cdot \beta_{k}^{(t-1)} + r_{k}^{bad}.
\end{align}
Within this architecture, the parameter $\lambda_h \in (0,1]$ operates as a historical decay factor. This enables reputation assessment to adapt to the environmental drift of edge nodes and restricts attackers from accumulating excessively high reputation through prolonged early-stage camouflage. Ultimately, the client\'s long-term historical utility value is derived as the mathematical expectation of this posterior distribution:
\begin{equation}
    HistPerf_{k}^{(t)} = \frac{\alpha_{k}^{(t)}}{\alpha_{k}^{(t)} + \beta_{k}^{(t)} + \varepsilon}
\end{equation}
A low $ for a specific node merely signifies an inability to furnish sufficient positive contributions recently. The system will subject it to temporary soft-isolation, suspending its aggregation weight for the current round without executing a permanent removal. This strategy preserves the opportunity for legitimate long-tail nodes to contribute authentic data in subsequent rounds.

**【中文原文】**
\textbf{(2) 瞬时风险流（安全一票否决权）}
与相对平滑的效用流不同，风险流面向潜在恶意攻击的瞬发事件。该流融合 TEE 远程证明、模型参数振幅、探针集损失波动和触发器激活等多个维度的安全探针（如 {probe}, r_{grad}, r_{trigger}, r_{pixel}$），在每一聚合轮次中直接抓取最大风险极值，以此构建具备一票否决效力的风险度量：
\begin{equation}
    Risk_{k}^{inst} = \max\{r_{report}, r_{grad}, r_{probe}, r_{pixel}, r_{trigger}, r_{sign}, r_{peer}, \dots \},
\end{equation}
随后借助指数平滑（EMA）以保存短时的危险印记（设 $\beta_r = 0.85$）：
\begin{equation}
    RiskEMA_{k}^{(t)} = \beta_{r} \cdot RiskEMA_{k}^{(t-1)} + (1 - \beta_{r}) \cdot Risk_{k}^{inst}.
\end{equation}
风险流和效用流的关键差别在于更新方向不同。$ 通过多轮证据平滑吸收短期波动，避免把长尾数据造成的低相似度直接判定为恶意；$ 则保留异常峰值的短时记忆，使一次强触发风险不会被历史高信誉立即稀释。二者在 $ 中汇合：效用流决定客户端是否值得继续保留贡献通道，风险流决定其当前贡献是否必须降权或隔离。

**【英文翻译】**
\textbf{(2) Instant Risk Stream (Security Veto Power)}
Distinct from the relatively smooth utility stream, the risk stream targets the instantaneous events characteristic of potential malicious attacks. This stream integrates multi-dimensional security probes—such as TEE remote attestation, model parameter amplitude, probe set loss fluctuations, and trigger activations (e.g., {probe}, r_{grad}, r_{trigger}, r_{pixel}$)—directly seizing the maximum risk extremum in every aggregation round to construct a risk metric equipped with veto power:
\begin{equation}
    Risk_{k}^{inst} = \max\{r_{report}, r_{grad}, r_{probe}, r_{pixel}, r_{trigger}, r_{sign}, r_{peer}, \dots \},
\end{equation}
Subsequently, exponential moving average (EMA) is utilized to preserve short-term danger imprints (setting $\beta_r = 0.85$):
\begin{equation}
    RiskEMA_{k}^{(t)} = \beta_{r} \cdot RiskEMA_{k}^{(t-1)} + (1 - \beta_{r}) \cdot Risk_{k}^{inst}.
\end{equation}
The critical distinction between the risk stream and the utility stream lies in their disparate updating directions. $ smoothly absorbs short-term fluctuations through multi-round evidence, evading the direct classification of low similarity—induced by long-tail data—as malicious behavior. Conversely, $ retains a short-term memory of abnormal peaks, ensuring that a robustly triggered risk is not instantaneously diluted by a high historical reputation. These two streams converge within the $: the utility stream determines whether the client merits retention of its contribution channel, while the risk stream dictates whether its current contribution necessitates demotion or isolation.

**【中文原文】**
以“潜伏-爆发”式投毒为例，某恶意客户端前期持续提交正常更新，其累积的历史效用 $ 可能已经接近 1.0；在第 $ 轮时，该节点突然混入包含语义触发器的恶意更新。若服务器仅依赖传统单维聚合评分，历史高分会掩盖本次异常跳变。而在本文构建的二维正交框架下，本次恶意操作会触发 {trigger}$ 等探针，导致风险流 $ 跃升并击穿隔离门限，从而阻断后门特征进入聚合路径。

**【英文翻译】**
Consider a "sleeper-burst" poisoning attack as an example. A malicious client continuously submits normal updates during the initial phases, potentially elevating its accumulated historical utility $ to near 1.0. At round $, this node suddenly injects a malicious update containing semantic triggers. If the server relied solely on a traditional single-dimensional aggregation score, the high historical score would obscure this anomalous leap. However, under the two-dimensional orthogonal framework formulated in this paper, this malicious operation activates probes such as {trigger}$, propelling the risk stream $ to surge and breach the isolation threshold, thereby blocking backdoor features from penetrating the aggregation pathway.

**【中文原文】**
在双流正交联合驱动下，客户端状态按图~\ref{fig:node_state_machine} 所示，在四类监管状态间动态流转：
\begin{itemize}
    \item \textbf{正常节点（NORMAL）}：平稳参与聚合。若风险攀升或历史贡献滑落，可被转入 SUSPECT 或 QUARANTINE。
    \item \textbf{嫌疑节点（SUSPECT）}：进入重点监控区域。若风险指标回落则可恢复为 NORMAL，若异常行为固化则实施升级隔离。
    \item \textbf{隔离节点（QUARANTINE）}：暂时取消模型聚合资格。经过一段观察期后可能恢复原状，或面临进一步的权限降级处理。
    \item \textbf{黑名单（BLACKLIST）}：一旦触发风险流硬阈值，即被执行永久封禁，并在底层 TEE 硬件认证端终止所有后续连接请求。
\end{itemize}

**【英文翻译】**
Propelled jointly by the dual-stream orthogonal mechanism, client states transition dynamically among four regulatory states, as depicted in Figure~\ref{fig:node_state_machine}:
\begin{itemize}
    \item \textbf{Normal Node (NORMAL)}: Participates steadily in aggregation. Should risk escalate or historical contribution diminish, the node may be demoted to SUSPECT or QUARANTINE.
    \item \textbf{Suspect Node (SUSPECT)}: Placed under intensive surveillance. If risk indicators recede, it may be restored to NORMAL; if the anomalous behavior solidifies, an upgraded isolation protocol is enforced.
    \item \textbf{Quarantined Node (QUARANTINE)}: Model aggregation privileges are temporarily suspended. Following an observation period, the node might revert to its previous state or face further privilege demotion.
    \item \textbf{Blacklist (BLACKLIST)}: Once the hard threshold of the risk stream is triggered, the node is permanently banned, and all subsequent connection requests are terminated at the underlying TEE hardware authentication tier.
\end{itemize}

\begin{figure}[H]
    \centering
    \includegraphics[width=0.9\textwidth]{fig4_state.pdf}
    \caption{历史效用演进与瞬发风险叠加驱动下的客户端监管状态转移自动机}
    \label{fig:node_state_machine}
\end{figure}

**【中文原文】**
最终，服务器依据硬件层面的信任背书（$）、当轮数据协同质量（$）以及演化所得的长期效用（$），融合成基础评分向量；进而叠加瞬时风险折扣率，输出用于指导后续阶段门控的最终权限融合因子 $：
\begin{align}
    RawScore_{k}^{base} & = (TrustScore_{k})^{\alpha} \cdot (ContentScore_{k})^{\beta} \cdot (HistPerf_{k}^{(t-1)})^{\gamma}, \
    RawScore_{k}        & = RawScore_{k}^{base} \cdot (1 - RiskEMA_{k}^{(t-1)})^{p},
\end{align}
其中，$\alpha,\beta,\gamma,p$ 控制各维度对最终聚合权重的影响强度。$ 提供客户端执行环境可信度，$ 提供本轮更新质量，$ 提供长期贡献记忆，$ 则以折扣项形式施加安全约束。该融合方式使低贡献节点不会被立即永久剔除，而高风险节点即使历史贡献较高也会被快速降权或隔离。

**【英文翻译】**
Ultimately, utilizing the hardware-level trust endorsement ($), the data collaboration quality of the current round ($), and the evolved long-term utility ($), the server fuses these metrics into a foundational scoring vector. Subsequently superimposing the instant risk discount rate, it yields the definitive privilege fusion factor $, which directs the gating in subsequent phases:
\begin{align}
    RawScore_{k}^{base} & = (TrustScore_{k})^{\alpha} \cdot (ContentScore_{k})^{\beta} \cdot (HistPerf_{k}^{(t-1)})^{\gamma}, \
    RawScore_{k}        & = RawScore_{k}^{base} \cdot (1 - RiskEMA_{k}^{(t-1)})^{p},
\end{align}
where $\alpha,\beta,\gamma,p$ dictate the intensity of influence each dimension exerts on the final aggregation weight. Specifically, $ provides the credibility of the client\'s execution environment, $ signifies the quality of the current-round update, $ furnishes the memory of long-term contributions, and $ imposes security constraints as a discount term. This fusion modality guarantees that low-contribution nodes are not instantaneously and permanently eliminated, while ensuring that high-risk nodes are rapidly demoted or isolated, regardless of their high historical contributions.

\begin{algorithm}[htbp]
    \caption{双流正交信任状态演化 (HistPerf \& RiskEMA)}
    \label{alg:phase3}
    \begin{algorithmic}[1]
        \REQUIRE $, 多维风险探针集合 $\{r_{probe}, r_{grad}, \dots\}$
        \ENSURE ^{(t)}$，瞬时风险流 ^{(t)}$，全局权值总分 $
        \STATE \textbf{流 A：历史效用流演化 (基于 Beta 信誉系统)}
        \STATE 计算全局内容得分均值 $\mu_{content}$ 与标准差 $\sigma_{content}$
        \FOR{通过准入的客户端 $}
        \STATE 提取正向增益证据 {k}^{good} \leftarrow \mathrm{clip}((ContentScore_k - \mu_{content}) / (\sigma_{content} + \varepsilon), 0, 1)$
        \STATE 提取负向衰减证据 {k}^{bad} \leftarrow 1 - r_{k}^{good}$
        \STATE 更新 Beta 参数 $\alpha_{k}^{(t)} \leftarrow \lambda_h \cdot \alpha_{k}^{(t-1)} + r_{k}^{good}$
        \STATE 更新 Beta 参数 $\beta_{k}^{(t)} \leftarrow \lambda_h \cdot \beta_{k}^{(t-1)} + r_{k}^{bad}$
        \STATE 计算期望效用 ^{(t)} \leftarrow \alpha_k^{(t)} / (\alpha_k^{(t)} + \beta_k^{(t)} + \varepsilon)$
        \ENDFOR
        \STATE \textbf{流 B：瞬时风险惩戒流演化 (一票否决权)}
        \FOR{每个客户端 $}
        \STATE 捕获瞬时风险极值 ^{inst} \leftarrow \max\{r_{report}, r_{grad}, r_{probe}, r_{pixel}, r_{trigger}\}$
        \STATE 更新 ^{(t)} \leftarrow \beta_r RiskEMA_k^{(t-1)} + (1-\beta_r) Risk_k^{inst}$
        \IF{^{(t)} > \text{隔离门限}$}
        \STATE 加入长期隔离黑名单  \leftarrow RiskIsolated \cup \{k\}$
        \ENDIF
        \ENDFOR
        \STATE \textbf{最终权限融合计算}
        \FOR{活跃客户端  \notin RiskIsolated$}
        \STATE 融合分数  \leftarrow (TrustScore_k)^\alpha (ContentScore_k)^\beta (HistPerf_k^{(t-1)})^\gamma$
        \STATE 风险折扣  \leftarrow RawScore_k \cdot (1 - RiskEMA_k^{(t-1)})^p$
        \ENDFOR
        \RETURN $\{HistPerf_k^{(t)}, RiskEMA_k^{(t)}, RawScore_k\}$
    \end{algorithmic}
\end{algorithm}

**【中文原文】**
\subsection{风险门控驱动的分层聚合}
隐蔽后门往往倾向于潜伏在深层网络参数中。在此情境下，若对全局整网执行无差别聚合，异常更新仍有可能发生跨层透传。针对这一潜在隐患，本文摒弃粗粒度的统一聚合模式，提出一种结合多维风险门控与约束规划思想的分层（Layer-wise）聚合机制（见图~\ref{fig:layer_gating}）。该阶段接收上一阶段输出的 $，并针对不同网络层分别决定“谁能进入本层聚合、以多大权重参与、其更新幅度是否需要裁剪”。

**【英文翻译】**
\subsection{风险门控驱动的分层聚合}
Stealthy backdoors frequently exhibit a propensity to lie dormant within deep network parameters. In such contexts, executing an indiscriminate aggregation across the entire global network might still permit anomalous updates to penetrate across layers. Addressing this latent hazard, this paper discards the coarse-grained, uniform aggregation paradigm, instead proposing a layer-wise aggregation mechanism synthesizing multi-dimensional risk gating and constrained programming concepts (see Figure~\ref{fig:layer_gating}). This stage ingests the $ generated in the preceding phase, independently determining for distinct network layers "who is eligible to enter the current layer\'s aggregation, with what magnitude of weight to participate, and whether their update amplitude requires clipping."

**【中文原文】**
首先，构建\textbf{多维风险门控网络（Risk Gating Network）}以动态感知各个网络层的脆弱性差异。设 $\mathcal{A}$ 为本轮未被软硬隔离的活跃客户端集合（$\mathcal{A} = \{k \mid k \notin RiskIsolated \land k \notin HistSoftIsolated\}$）。对任意网络层 $，其综合防御门控敏感度 {total}^{(l)}$ 建模为隐私、效用与安全三个维度的线性组合：
\begin{align}
    S_{privacy}^{(l)}  & = \exp\left(-\tau_{p} \frac{l}{L}\right),                                                                                                          \
    S_{utility}^{(l)}  & = \frac{\|g_{ref}^{(l)}\|_{2}}{\max_{m}\|g_{ref}^{(m)}\|_{2} + \varepsilon},                                                                       \
    S_{security}^{(l)} & = 1 - \frac{\sum_{k\in\mathcal{A}}TrustScore_{k}\cdot\cos(\Delta W_{k}^{(l)}, g_{ref}^{(l)})}{\sum_{k\in\mathcal{A}}TrustScore_{k} + \varepsilon}.
\end{align}
基于上述三项指标，经加权合成得到 {total}^{(l)} = w_p S_{privacy}^{(l)} + w_u S_{utility}^{(l)} + w_s S_{security}^{(l)}$。其中，{privacy}^{(l)}$ 描述不同层的隐私暴露敏感性，{utility}^{(l)}$ 反映该层对全局优化方向的贡献强度，{security}^{(l)}$ 则度量该层更新与参考方向的偏离风险。门控网络会根据每一层的实时风险波动，动态输出该层的准入门槛 $\theta^{(l)} = \mu_{base} + \lambda_s \cdot S_{total}^{(l)}$ 以及自适应裁剪边界 ^{(l)} = C_{base} / (S_{total}^{(l)} + \varepsilon_c)$。当某一层的综合风险升高时，$\theta^{(l)}$ 随之提高，低可信客户端更难进入该层聚合；^{(l)}$ 同时收紧，防止高幅值更新对模型参数产生过大牵引。

**【英文翻译】**
First, a \textbf{Multi-Dimensional Risk Gating Network} is constructed to dynamically perceive the varying vulnerabilities across distinct network layers. Let $\mathcal{A}$ represent the set of active clients in the current round that have evaded both soft and hard isolation ($\mathcal{A} = \{k \mid k \notin RiskIsolated \land k \notin HistSoftIsolated\}$). For an arbitrary network layer $, its comprehensive defensive gating sensitivity {total}^{(l)}$ is modeled as a linear combination spanning privacy, utility, and security dimensions:
\begin{align}
    S_{privacy}^{(l)}  & = \exp\left(-\tau_{p} \frac{l}{L}\right),                                                                                                          \
    S_{utility}^{(l)}  & = \frac{\|g_{ref}^{(l)}\|_{2}}{\max_{m}\|g_{ref}^{(m)}\|_{2} + \varepsilon},                                                                       \
    S_{security}^{(l)} & = 1 - \frac{\sum_{k\in\mathcal{A}}TrustScore_{k}\cdot\cos(\Delta W_{k}^{(l)}, g_{ref}^{(l)})}{\sum_{k\in\mathcal{A}}TrustScore_{k} + \varepsilon}.
\end{align}
Based on these three metrics, the weighted synthesis yields {total}^{(l)} = w_p S_{privacy}^{(l)} + w_u S_{utility}^{(l)} + w_s S_{security}^{(l)}$. Herein, {privacy}^{(l)}$ delineates the privacy exposure sensitivity of varied layers, {utility}^{(l)}$ reflects the layer\'s contribution intensity toward the global optimization direction, and {security}^{(l)}$ measures the deviation risk of the layer\'s update relative to the reference direction. The gating network, reacting to the real-time risk fluctuations of each layer, dynamically outputs the admission threshold $\theta^{(l)} = \mu_{base} + \lambda_s \cdot S_{total}^{(l)}$ and an adaptive clipping boundary ^{(l)} = C_{base} / (S_{total}^{(l)} + \varepsilon_c)$. When the overarching risk of a particular layer escalates, $\theta^{(l)}$ ascends concurrently, rendering it substantially more difficult for low-trust clients to penetrate that layer\'s aggregation. Simultaneously, ^{(l)}$ tightens to preclude high-amplitude updates from exerting excessive traction on the model parameters.

**【中文原文】**
其次，引入\textbf{约束规划思想（Optimization Perspective）}执行幸存者权重重归一化。系统排除了  < \theta^{(l)}$ 的高风险节点后，构建本层的幸存子集 $\Phi^{(l)}$。在此环节中，聚合权重的分配被转化为了一个可信域内的投影优化过程，力求在安全约束内最大化高信誉节点的贡献：
\begin{equation}
    \tilde{w}_{k}^{(l)} = \frac{RawScore_{k}}{\sum_{j\in\Phi^{(l)}}RawScore_{j} + \varepsilon}, \quad \text{s.t.} \sum_{k\in\Phi^{(l)}} \tilde{w}_{k}^{(l)} \approx 1, \tilde{w}_{k}^{(l)} \ge 0.
\end{equation}
该重归一化过程确保被门控保留下来的客户端仍能形成有效聚合权重，避免因部分节点被剔除而导致该层更新幅度失衡。

**【英文翻译】**
Subsequently, an \textbf{Optimization Perspective} is introduced to execute the re-normalization of survivor weights. Having excised the high-risk nodes where  < \theta^{(l)}$, the system formulates the survivor subset $\Phi^{(l)}$ for the current layer. During this procedure, the allocation of aggregation weights transforms into a projection optimization process within a trusted domain, striving to maximize the contributions of highly reputable nodes within security constraints:
\begin{equation}
    \tilde{w}_{k}^{(l)} = \frac{RawScore_{k}}{\sum_{j\in\Phi^{(l)}}RawScore_{j} + \varepsilon}, \quad \text{s.t.} \sum_{k\in\Phi^{(l)}} \tilde{w}_{k}^{(l)} \approx 1, \tilde{w}_{k}^{(l)} \ge 0.
\end{equation}
This re-normalization process guarantees that the clients retained by the gatekeeping mechanism can still establish an effective aggregation weight, effectively averting imbalances in the layer\'s update magnitude that might otherwise arise from the elimination of certain nodes.

**【中文原文】**
最后，实施\textbf{动态 L2 裁剪与分层组装}。为防止幸存恶意节点在极端方向上拉偏模型，采用缩放算子将偏离预期振幅的更新量强制投影至安全球内，并逐层完成加权聚合：
\begin{equation}
    \widehat{\Delta W}_{k}^{(l)} = \frac{\Delta W_{k}^{(l)}}{\max\left(1, \frac{\|\Delta W_{k}^{(l)}\|_{2}}{C^{(l)}}\right)}, \quad \Delta W_{global}^{(l)} = \sum_{k\in\Phi^{(l)}}\tilde{w}_{k}^{(l)} \cdot \widehat{\Delta W}_{k}^{(l)}.
\end{equation}

**【英文翻译】**
Finally, the framework enforces \textbf{Dynamic L2 Clipping and Layered Assembly}. To prevent surviving malicious nodes from skewing the model toward extreme directions, a scaling operator is deployed to forcibly project update quantities that deviate from anticipated amplitudes back into a secure sphere, culminating in the layer-wise weighted aggregation:
\begin{equation}
    \widehat{\Delta W}_{k}^{(l)} = \frac{\Delta W_{k}^{(l)}}{\max\left(1, \frac{\|\Delta W_{k}^{(l)}\|_{2}}{C^{(l)}}\right)}, \quad \Delta W_{global}^{(l)} = \sum_{k\in\Phi^{(l)}}\tilde{w}_{k}^{(l)} \cdot \widehat{\Delta W}_{k}^{(l)}.
\end{equation}

**【中文原文】**
为说明该机制的实际运作逻辑，可以考察一个隐蔽后门植入案例。假设攻击者试图在网络深层的全连接层嵌入语义触发器；由于恶意更新偏离正常分布，安全敏感度 {security}^{(l)}$ 会明显升高。此时门控网络从两个方向介入：一方面抬高信誉门槛 $\theta^{(l)}$，使低 $ 节点无法进入该层聚合；另一方面缩小 ^{(l)}$，限制幸存更新的参数范数。浅层特征提取层若风险较低，则可保留相对宽松的门槛与裁剪边界。通过这种层级差异化控制，系统能够削弱深层后门特征向全局模型的渗透，同时减少对合法浅层通用特征的过度压制。

**【英文翻译】**
To illustrate the practical operational logic of this mechanism, consider the case of stealthy backdoor implantation. Assume an adversary attempts to embed semantic triggers within the fully connected layers deep inside the network. Because the malicious updates diverge from the normal distribution, the security sensitivity {security}^{(l)}$ will markedly elevate. At this juncture, the gating network intervenes from two directions. First, it elevates the reputation threshold $\theta^{(l)}$, effectively barring nodes with low  from entering this layer\'s aggregation. Second, it shrinks ^{(l)}$, restricting the parameter norms of the surviving updates. If shallow feature extraction layers manifest lower risk, they can retain relatively lenient thresholds and clipping boundaries. Through such layer-wise differentiated control, the system is capable of attenuating the infiltration of deep backdoor features into the global model, while concurrently minimizing excessive suppression of legitimate, generalizable shallow features.

\begin{figure}[htbp]
    \centering
    \includegraphics[width=0.95\textwidth]{fig5_layer.pdf}
    \caption{风险门控驱动的分层自适应审查与动态裁剪机制示意图}
    \label{fig:layer_gating}
\end{figure}

\begin{algorithm}[htbp]
    \caption{基于风险门控的分层差异化聚合与动态裁剪}
    \label{alg:phase4}
    \begin{algorithmic}[1]
        \REQUIRE 活跃节点 $\mathcal{A}$，分数 $，分层更新梯度 $\{\Delta W_k^{(l)}\}$，网络深度 $
        \ENSURE 本轮全局安全梯度 $\Delta W_{global}$
        \STATE 初始化全局增量 $\Delta W_{global} \leftarrow 0$
        \FOR{网络每一层  = 1, 2, \dots, L$}
        \STATE \textbf{步骤 1: 层级敏感度三维联合测算}
        \STATE 隐私敏感度 {privacy}^{(l)} \leftarrow \exp(-\tau_p \cdot l/L)$
        \STATE 效用敏感度 {utility}^{(l)} \leftarrow \|g_{ref}^{(l)}\|_2 / \max_m\|g_{ref}^{(m)}\|_2$
        \STATE 安全敏感度 {security}^{(l)} \leftarrow 1 - \frac{\sum_{k\in\mathcal{A}} TrustScore_k \cos(\Delta W_k^{(l)}, g_{ref}^{(l)})}{\sum_{k\in\mathcal{A}} TrustScore_k + \varepsilon}$
        \STATE 总防御诉求敏感度 {total}^{(l)} \leftarrow w_p S_{privacy}^{(l)} + w_u S_{utility}^{(l)} + w_s S_{security}^{(l)}$
        \STATE \textbf{步骤 2: 动态风险门控与 L2 自适应裁剪}
        \STATE 提高本层安全入场分数门槛 $\theta^{(l)} \leftarrow \mu_{base} + \lambda_s \cdot S_{total}^{(l)}$
        \STATE 收紧本层恶意振幅裁剪边界 ^{(l)} \leftarrow C_{base} / (S_{total}^{(l)} + \varepsilon_c)$
        \STATE \textbf{步骤 3: 幸存节点挑选与二次重校准}
        \STATE 筛选本层幸存者名单 $\Phi^{(l)} \leftarrow \{k \in \mathcal{A} \mid RawScore_k \ge \theta^{(l)}\}$
        \STATE 对幸存者重新归一化有效权重 $\tilde{w}_k^{(l)} \leftarrow RawScore_k / \sum_{j\in\Phi^{(l)}} RawScore_j$
        \STATE 按规则执行 L2 等比缩小 $\widehat{\Delta W}_k^{(l)} \leftarrow \Delta W_k^{(l)} / \max(1, \|\Delta W_k^{(l)}\|_2 / C^{(l)})$
        \STATE \textbf{步骤 4: 分层合并拼接}
        \STATE 计算本层安全聚合增量 $\Delta W_{global}^{(l)} \leftarrow \sum_{k\in\Phi^{(l)}} \tilde{w}_k^{(l)} \cdot \widehat{\Delta W}_k^{(l)}$
        \STATE 拼接并写入全局模型更新量 $\Delta W_{global} \leftarrow \Delta W_{global} \cup \Delta W_{global}^{(l)}$
        \ENDFOR
        \RETURN $\Delta W_{global}$
    \end{algorithmic}
\end{algorithm}

**【中文原文】**
\subsection{模型更新下发与知识留存}
分层聚合完成后，服务器将安全增量应用到全局模型：{global}^{new} = W_{global}^{old} + \Delta W_{global}$，并同步下发更新后的模型及客户端状态（含 $）。至此形成一轮完整闭环，在保证收敛的同时持续过滤恶意更新。

**【英文翻译】**
\subsection{模型更新下发与知识留存}
Upon the completion of layered aggregation, the server applies the secure increment to the global model: {global}^{new} = W_{global}^{old} + \Delta W_{global}$, and synchronously distributes the updated model along with the clients\' states (including $). This culminates in a complete closed loop, ensuring convergence while relentlessly filtering out malicious updates.

**【中文原文】**
\subsection{双流正交解耦的理论保证 (Theoretical Analysis)}
传统单一信誉分数（如简单余弦累加）本质上将高维行为压缩到单轴判断。在强 Non-IID 场景下，这会使得漏检（FNR）与误杀（FPR）的冲突加剧。本节给出双流正交机制的理论分析。

**【英文翻译】**
\subsection{双流正交解耦的理论保证 (Theoretical Analysis)}
Traditional single reputation scores (such as simple cosine accumulation) inherently compress high-dimensional behaviors into single-axis judgments. Under formidable Non-IID scenarios, this invariably exacerbates the conflict between false negative rates (FNR) and false positive rates (FPR). This section articulates the theoretical analysis of the dual-stream orthogonal mechanism.

**【中文原文】**
\textbf{引理 1（长尾节点的方差收敛特性，Lemma 1）}
设长尾合法客户端 $ 的单轮内容分 {k}^{(t)}$ 服从期望 $\mu_{clean}$、方差 $\sigma_{clean}^2$ 的扰动分布。在刚性阈值 $\tau_{hard}$ 下，若 $\tau_{hard} > \mu_{clean} - \sigma_{clean}$，该节点将有较高概率被持续淘汰。采用历史效用流平滑后，其稳态期望满足 $\mathbb{E}[HistPerf_k^{(\infty)}] = \mu_{clean}$，且方差收敛为：
\begin{equation}
    \operatorname{Var}(HistPerf_{k}^{(\infty)}) = \frac{1-\beta_h}{1+\beta_h} \sigma_{clean}^{2}
\end{equation}
由于 /bin/bash < \beta_h < 1$，当 $\beta_h \to 1$ 时，短时扰动被显著平滑。只要 $\mu_{clean}$ 高于生存阈值，历史效用流可作为低通滤波器提高合法节点长期存活概率，理论上支持 $\lim_{t \to \infty} \text{FPR} = 0$。

**【英文翻译】**
\textbf{Lemma 1 (Variance Convergence Property of Long-Tail Nodes)}
Assume that the single-round content score {k}^{(t)}$ of a legitimate long-tail client $ follows a perturbed distribution with expectation $\mu_{clean}$ and variance $\sigma_{clean}^2$. Under a rigid threshold $\tau_{hard}$, if $\tau_{hard} > \mu_{clean} - \sigma_{clean}$, this node faces a high probability of sustained elimination. Upon adopting the historical utility stream for smoothing, its steady-state expectation satisfies $\mathbb{E}[HistPerf_k^{(\infty)}] = \mu_{clean}$, and the variance converges to:
\begin{equation}
    \operatorname{Var}(HistPerf_{k}^{(\infty)}) = \frac{1-\beta_h}{1+\beta_h} \sigma_{clean}^{2}
\end{equation}
Given that /bin/bash < \beta_h < 1$, as $\beta_h \to 1$, short-term perturbations are markedly smoothed. As long as $\mu_{clean}$ exceeds the survival threshold, the historical utility stream functions as a low-pass filter, enhancing the long-term survival probability of legitimate nodes and theoretically supporting $\lim_{t \to \infty} \text{FPR} = 0$.

**【中文原文】**
\textbf{引理 2（高阶潜伏投毒的瞬时冲激响应，Lemma 2）}
对“长期伪装、间歇爆发”的后门节点 $，即使其前期累积了较高 $，在攻击轮次仍会触发异常探针峰值（$\exists r \in \{r_{grad}, r_{probe}, r_{trigger}\}, r \gg 1$）。由于 ^{inst}$ 取多探针最大值，且 EMA 对输入单调，RiskEMA 轨迹满足下界：
\begin{equation}
    RiskEMA_m^{(t)} \ge \max \left( \beta_r \cdot RiskEMA_m^{(t-1)},\ \mathcal{F}_{probe}(r_{grad}, r_{probe}, r_{trigger}) \right)
\end{equation}
当 $\mathcal{F}_{probe}$ 触发异常突变时，风险值会在短时间内跃升并逼近或超过门限，从而触发隔离。

**【英文翻译】**
\textbf{Lemma 2 (Instantaneous Impulse Response to High-Order Sleeper Poisoning)}
Regarding a backdoor node $ executing a strategy of "long-term camouflage followed by intermittent bursts," even if it has accrued a high $ during early stages, it will invariably trigger an abnormal probe peak during the attack round ($\exists r \in \{r_{grad}, r_{probe}, r_{trigger}\}, r \gg 1$). Because ^{inst}$ seizes the maximum value across multiple probes, and the EMA maintains monotonicity concerning the input, the RiskEMA trajectory satisfies the following lower bound:
\begin{equation}
    RiskEMA_m^{(t)} \ge \max \left( \beta_r \cdot RiskEMA_m^{(t-1)},\ \mathcal{F}_{probe}(r_{grad}, r_{probe}, r_{trigger}) \right)
\end{equation}
When $\mathcal{F}_{probe}$ activates an anomalous mutation, the risk value surges rapidly, approaching or breaching the threshold within a brief timeframe, thereby triggering isolation.

**【中文原文】**
\textbf{定理 1（双流熔断正交解耦，Theorem 1）}
\textit{在双流机制下，诚实长尾节点的高方差更新由 $ 通道平滑吸收；恶意攻击的突发行为则由 ^{inst}$ 通道快速放大并触发熔断。两类信号在判别空间中被解耦处理，从而缓解单分数机制难以同时优化 $\text{FPR}$ 与 $\text{ASR}$ 的矛盾。}

**【英文翻译】**
\textbf{Theorem 1 (Dual-Stream Circuit Breaking and Orthogonal Decoupling)}
\textit{Under the dual-stream mechanism, the high-variance updates of honest long-tail nodes are smoothly absorbed by the $ channel. Conversely, the abrupt behaviors characteristic of malicious attacks are swiftly amplified by the ^{inst}$ channel, triggering an immediate circuit break. These two categories of signals are decoupled and processed within distinct discriminative spaces, thereby alleviating the profound paradox wherein single-score mechanisms struggle to simultaneously optimize both FPR and ASR.}

\begin{algorithm}[htbp]
    \caption{基于 TEE 硬件锚点与纯净参考的准入与内容审查}
    \label{alg:phase12}
    \begin{algorithmic}[1]
        \REQUIRE 客户端集合 $\mathcal{C}$，本轮收到的参数更新 $\{\Delta W_k\}_{k\in\mathcal{C}}$，上轮状态 $RiskEMA^{(t-1)}$
        \ENSURE $TrustScore_k$, $ContentScore_k$, 有效参考基准 $g_{root}$
        \STATE \textbf{第一阶段：硬件锚定与动态信任度量}
        \FOR{每个客户端 $k \in \mathcal{C}$}
        \IF{$M_{attest,k} == 0$ (TEE 远程证明失败)}
        \STATE 拒绝接入：$TrustScore_k \leftarrow 0$，并跳过本轮
        \ELSE
        \STATE \textit{TEE 内部}: 记录行为序列 $\mathcal{X}_k = \{ \Delta \text{grad}, \Delta \text{loss}, \text{instr\_dist} \}$
        \STATE 计算信息熵 $H_k \leftarrow -\sum p(x_i) \log p(x_i)$
        \STATE 将熵映射为测量噪声 $R_k \leftarrow \exp(\lambda \cdot H_k)$
        \STATE \textit{卡尔曼滤波更新}:
        \STATE 信任估计 $\hat{T}_k$, 协方差 $P_k \leftarrow \mathrm{KalmanFilter}(H_k, \text{前序状态})$
        \STATE 门禁信任分 $TrustScore_k \leftarrow \hat{T}_k \cdot \frac{1}{1 + P_k}$
        \ENDIF
        \ENDFOR
        \STATE \textbf{第二阶段：参考方向构建与协同一致性审查}
        \IF{具备服务器纯净验证集数据}
        \STATE 提取真实指导梯度 $g_{root} \leftarrow g_{root\_clean}$
        \ELSE
        \STATE 计算非线性权重 $\omega_k^{ref} \leftarrow TrustScore_k \cdot (1 - RiskEMA_k^{(t-1)})^2$
        \STATE 生成降级纯净锚点 $g_{root} \leftarrow \sum_k (\omega_k^{ref} \Delta W_k) / \sum_j \omega_j^{ref}$
        \ENDIF
        \FOR{通过准入的活跃客户端 $k$}
        \STATE 全局贡献分 $S_{contrib,k} \leftarrow \max(0, \alpha_1 + \alpha_2 \cos(\Delta W_k, g_{root}))$
        \STATE 群体协作分 $S_{consist,k} \leftarrow \frac{\sum_{j \neq k} TrustScore_j \max(0, \alpha_1 + \alpha_2 \cos(\Delta W_k, \Delta W_j))}{\sum_{j \neq k} TrustScore_j + \varepsilon}$
        \STATE 调和内容分 $ContentScore_k \leftarrow \frac{(1+\beta_{fusion}^2)S_{consist,k} S_{contrib,k}}{\beta_{fusion}^2 S_{consist,k} + S_{contrib,k} + \varepsilon}$
        \ENDFOR
        \RETURN $\{TrustScore_k, ContentScore_k, g_{root}\}$
    \end{algorithmic}
\end{algorithm}

**【中文原文】**
\subsection{历史效用与瞬时风险的双流演化}
在强 Non-IID（非独立同分布）边缘计算场景中，传统“低分即淘汰”的策略往往混淆了“数据长尾性导致的低效用”与“恶意投毒导致的高风险”，容易引发严重的误杀（FPR）。为破解这一困境，本研究构建二维正交解耦空间，将客户端的状态演化拆分为两个相互独立但在决策阶段汇合的时序流：用于长期能力评估的\textbf{历史效用流（$HistPerf$）}，以及用于捕捉突发异常的\textbf{瞬时风险流（$RiskEMA$）}。前者解决“是否长期有贡献”，后者解决“本轮是否存在安全风险”。两类信号不在同一轴上互相抵消，从而缓解传统单维评分体系中误检与漏检的内在冲突。

**【英文翻译】**
\subsection{历史效用与瞬时风险的双流演化}
In edge computing scenarios characterized by strong Non-IID (non-independent and identically distributed) data, the conventional "low-score equals elimination" strategy frequently conflates "low utility induced by data long-tailness" with "high risk caused by malicious poisoning," leading to severe false positive rates (FPR). To disentangle this dilemma, this study constructs a two-dimensional orthogonal decoupling space. The state evolution of clients is segregated into two mutually independent temporal streams that converge during the decision-making phase: a \textbf{historical utility stream ($HistPerf$)} dedicated to evaluating long-term capability, and an \textbf{instant risk stream ($RiskEMA$)} tailored for capturing sudden anomalies. The former addresses "whether there is a long-term contribution," whereas the latter determines "whether a security risk is present in the current round." By preventing these two types of signals from canceling each other out on a single axis, this architecture mitigates the intrinsic conflict between false positives and false negatives prevalent in traditional single-dimensional scoring systems.

**【中文原文】**
\textbf{(1) 历史效用流（基于贝叶斯后验推断）}
该支流对节点的持续贡献进行长期评估。在此，本研究引入贝叶斯推断框架（Beta 信誉系统），将客户端 $k$ 提供高质量梯度的概率建模为 Beta 分布 $\text{Beta}(\alpha_k, \beta_k)$。假设其初始状态为无信息先验 $\text{Beta}(1,1)$，其中 $\alpha_k$ 记录其累积的良性表现，$\beta_k$ 则映射其低质量行为。在联邦学习的每一轮次中，系统基于当轮内容得分 $ContentScore_k$ 提取正向增益证据 $r_{k}^{good}$ 与负向衰减证据 $r_{k}^{bad}$，并按后验更新方式累积历史证据：
\begin{align}
    r_{k}^{good}     & = \mathrm{clip}\left(\frac{ContentScore_{k} - \mu_{content}}{\sigma_{content} + \varepsilon}, 0, 1\right), \\
    r_{k}^{bad}      & = 1 - r_{k}^{good},                                                                                        \\
    \alpha_{k}^{(t)} & = \lambda_h \cdot \alpha_{k}^{(t-1)} + r_{k}^{good},                                                       \\
    \beta_{k}^{(t)}  & = \lambda_h \cdot \beta_{k}^{(t-1)} + r_{k}^{bad}.
\end{align}
在此体系下，参数 $\lambda_h \in (0,1]$ 作为历史衰减因子，使信誉评估能够适应边缘节点的设备环境漂移，并限制攻击者通过前期长时间伪装累积过高信誉。客户端的长期历史效用值最终取为该后验分布的数学期望：
\begin{equation}
    HistPerf_{k}^{(t)} = \frac{\alpha_{k}^{(t)}}{\alpha_{k}^{(t)} + \beta_{k}^{(t)} + \varepsilon}
\end{equation}
当某节点的 $HistPerf$ 偏低时，仅意味着其近期未能提供充足的正向贡献。系统将对其执行临时软隔离（Soft-Isolation），暂停其本轮聚合权重，但不作永久移除处理。这样可以保留长尾合法节点后续重新贡献真实数据的机会。

**【英文翻译】**
\textbf{(1) Historical Utility Stream (Based on Bayesian Posterior Inference)}
This tributary undertakes the long-term evaluation of a node's sustained contributions. Here, the research introduces a Bayesian inference framework (the Beta reputation system), modeling the probability of client $k$ providing high-quality gradients as a Beta distribution, $\text{Beta}(\alpha_k, \beta_k)$. Assuming an initial state of an uninformative prior $\text{Beta}(1,1)$, $\alpha_k$ records the accumulated benign performance, while $\beta_k$ maps low-quality behavior. In each round of federated learning, the system extracts positive gain evidence $r_{k}^{good}$ and negative decay evidence $r_{k}^{bad}$ based on the current round's content score $ContentScore_k$, subsequently accumulating historical evidence via posterior updating:
\begin{align}
    r_{k}^{good}     & = \mathrm{clip}\left(\frac{ContentScore_{k} - \mu_{content}}{\sigma_{content} + \varepsilon}, 0, 1\right), \\
    r_{k}^{bad}      & = 1 - r_{k}^{good},                                                                                        \\
    \alpha_{k}^{(t)} & = \lambda_h \cdot \alpha_{k}^{(t-1)} + r_{k}^{good},                                                       \\
    \beta_{k}^{(t)}  & = \lambda_h \cdot \beta_{k}^{(t-1)} + r_{k}^{bad}.
\end{align}
Within this architecture, the parameter $\lambda_h \in (0,1]$ operates as a historical decay factor. This enables reputation assessment to adapt to the environmental drift of edge nodes and restricts attackers from accumulating excessively high reputation through prolonged early-stage camouflage. Ultimately, the client's long-term historical utility value is derived as the mathematical expectation of this posterior distribution:
\begin{equation}
    HistPerf_{k}^{(t)} = \frac{\alpha_{k}^{(t)}}{\alpha_{k}^{(t)} + \beta_{k}^{(t)} + \varepsilon}
\end{equation}
A low $HistPerf$ for a specific node merely signifies an inability to furnish sufficient positive contributions recently. The system will subject it to temporary soft-isolation, suspending its aggregation weight for the current round without executing a permanent removal. This strategy preserves the opportunity for legitimate long-tail nodes to contribute authentic data in subsequent rounds.

**【中文原文】**
\textbf{(2) 瞬时风险流（安全一票否决权）}
与相对平滑的效用流不同，风险流面向潜在恶意攻击的瞬发事件。该流融合 TEE 远程证明、模型参数振幅、探针集损失波动和触发器激活等多个维度的安全探针（如 $r_{probe}, r_{grad}, r_{trigger}, r_{pixel}$），在每一聚合轮次中直接抓取最大风险极值，以此构建具备一票否决效力的风险度量：
\begin{equation}
    Risk_{k}^{inst} = \max\{r_{report}, r_{grad}, r_{probe}, r_{pixel}, r_{trigger}, r_{sign}, r_{peer}, \dots \},
\end{equation}
随后借助指数平滑（EMA）以保存短时的危险印记（设 $\beta_r = 0.85$）：
\begin{equation}
    RiskEMA_{k}^{(t)} = \beta_{r} \cdot RiskEMA_{k}^{(t-1)} + (1 - \beta_{r}) \cdot Risk_{k}^{inst}.
\end{equation}
风险流和效用流的关键差别在于更新方向不同。$HistPerf$ 通过多轮证据平滑吸收短期波动，避免把长尾数据造成的低相似度直接判定为恶意；$RiskEMA$ 则保留异常峰值的短时记忆，使一次强触发风险不会被历史高信誉立即稀释。二者在 $RawScore$ 中汇合：效用流决定客户端是否值得继续保留贡献通道，风险流决定其当前贡献是否必须降权或隔离。

**【英文翻译】**
\textbf{(2) Instant Risk Stream (Security Veto Power)}
Distinct from the relatively smooth utility stream, the risk stream targets the instantaneous events characteristic of potential malicious attacks. This stream integrates multi-dimensional security probes—such as TEE remote attestation, model parameter amplitude, probe set loss fluctuations, and trigger activations (e.g., $r_{probe}, r_{grad}, r_{trigger}, r_{pixel}$)—directly seizing the maximum risk extremum in every aggregation round to construct a risk metric equipped with veto power:
\begin{equation}
    Risk_{k}^{inst} = \max\{r_{report}, r_{grad}, r_{probe}, r_{pixel}, r_{trigger}, r_{sign}, r_{peer}, \dots \},
\end{equation}
Subsequently, exponential moving average (EMA) is utilized to preserve short-term danger imprints (setting $\beta_r = 0.85$):
\begin{equation}
    RiskEMA_{k}^{(t)} = \beta_{r} \cdot RiskEMA_{k}^{(t-1)} + (1 - \beta_{r}) \cdot Risk_{k}^{inst}.
\end{equation}
The critical distinction between the risk stream and the utility stream lies in their disparate updating directions. $HistPerf$ smoothly absorbs short-term fluctuations through multi-round evidence, evading the direct classification of low similarity—induced by long-tail data—as malicious behavior. Conversely, $RiskEMA$ retains a short-term memory of abnormal peaks, ensuring that a robustly triggered risk is not instantaneously diluted by a high historical reputation. These two streams converge within the $RawScore$: the utility stream determines whether the client merits retention of its contribution channel, while the risk stream dictates whether its current contribution necessitates demotion or isolation.

**【中文原文】**
以“潜伏-爆发”式投毒为例，某恶意客户端前期持续提交正常更新，其累积的历史效用 $HistPerf_k$ 可能已经接近 1.0；在第 $T$ 轮时，该节点突然混入包含语义触发器的恶意更新。若服务器仅依赖传统单维聚合评分，历史高分会掩盖本次异常跳变。而在本文构建的二维正交框架下，本次恶意操作会触发 $r_{trigger}$ 等探针，导致风险流 $RiskEMA_k$ 跃升并击穿隔离门限，从而阻断后门特征进入聚合路径。

**【英文翻译】**
Consider a "sleeper-burst" poisoning attack as an example. A malicious client continuously submits normal updates during the initial phases, potentially elevating its accumulated historical utility $HistPerf_k$ to near 1.0. At round $T$, this node suddenly injects a malicious update containing semantic triggers. If the server relied solely on a traditional single-dimensional aggregation score, the high historical score would obscure this anomalous leap. However, under the two-dimensional orthogonal framework formulated in this paper, this malicious operation activates probes such as $r_{trigger}$, propelling the risk stream $RiskEMA_k$ to surge and breach the isolation threshold, thereby blocking backdoor features from penetrating the aggregation pathway.

**【中文原文】**
在双流正交联合驱动下，客户端状态按图~\ref{fig:node_state_machine} 所示，在四类监管状态间动态流转：
\begin{itemize}
    \item \textbf{正常节点（NORMAL）}：平稳参与聚合。若风险攀升或历史贡献滑落，可被转入 SUSPECT 或 QUARANTINE。
    \item \textbf{嫌疑节点（SUSPECT）}：进入重点监控区域。若风险指标回落则可恢复为 NORMAL，若异常行为固化则实施升级隔离。
    \item \textbf{隔离节点（QUARANTINE）}：暂时取消模型聚合资格。经过一段观察期后可能恢复原状，或面临进一步的权限降级处理。
    \item \textbf{黑名单（BLACKLIST）}：一旦触发风险流硬阈值，即被执行永久封禁，并在底层 TEE 硬件认证端终止所有后续连接请求。
\end{itemize}

**【英文翻译】**
Propelled jointly by the dual-stream orthogonal mechanism, client states transition dynamically among four regulatory states, as depicted in Figure~\ref{fig:node_state_machine}:
\begin{itemize}
    \item \textbf{Normal Node (NORMAL)}: Participates steadily in aggregation. Should risk escalate or historical contribution diminish, the node may be demoted to SUSPECT or QUARANTINE.
    \item \textbf{Suspect Node (SUSPECT)}: Placed under intensive surveillance. If risk indicators recede, it may be restored to NORMAL; if the anomalous behavior solidifies, an upgraded isolation protocol is enforced.
    \item \textbf{Quarantined Node (QUARANTINE)}: Model aggregation privileges are temporarily suspended. Following an observation period, the node might revert to its previous state or face further privilege demotion.
    \item \textbf{Blacklist (BLACKLIST)}: Once the hard threshold of the risk stream is triggered, the node is permanently banned, and all subsequent connection requests are terminated at the underlying TEE hardware authentication tier.
\end{itemize}

\begin{figure}[H]
    \centering
    \includegraphics[width=0.9\textwidth]{fig4_state.pdf}
    \caption{历史效用演进与瞬发风险叠加驱动下的客户端监管状态转移自动机}
    \label{fig:node_state_machine}
\end{figure}

**【中文原文】**
最终，服务器依据硬件层面的信任背书（$TrustScore$）、当轮数据协同质量（$ContentScore$）以及演化所得的长期效用（$HistPerf$），融合成基础评分向量；进而叠加瞬时风险折扣率，输出用于指导后续阶段门控的最终权限融合因子 $RawScore_k$：
\begin{align}
    RawScore_{k}^{base} & = (TrustScore_{k})^{\alpha} \cdot (ContentScore_{k})^{\beta} \cdot (HistPerf_{k}^{(t-1)})^{\gamma}, \\
    RawScore_{k}        & = RawScore_{k}^{base} \cdot (1 - RiskEMA_{k}^{(t-1)})^{p},
\end{align}
其中，$\alpha,\beta,\gamma,p$ 控制各维度对最终聚合权重的影响强度。$TrustScore$ 提供客户端执行环境可信度，$ContentScore$ 提供本轮更新质量，$HistPerf$ 提供长期贡献记忆，$RiskEMA$ 则以折扣项形式施加安全约束。该融合方式使低贡献节点不会被立即永久剔除，而高风险节点即使历史贡献较高也会被快速降权或隔离。

**【英文翻译】**
Ultimately, utilizing the hardware-level trust endorsement ($TrustScore$), the data collaboration quality of the current round ($ContentScore$), and the evolved long-term utility ($HistPerf$), the server fuses these metrics into a foundational scoring vector. Subsequently superimposing the instant risk discount rate, it yields the definitive privilege fusion factor $RawScore_k$, which directs the gating in subsequent phases:
\begin{align}
    RawScore_{k}^{base} & = (TrustScore_{k})^{\alpha} \cdot (ContentScore_{k})^{\beta} \cdot (HistPerf_{k}^{(t-1)})^{\gamma}, \\
    RawScore_{k}        & = RawScore_{k}^{base} \cdot (1 - RiskEMA_{k}^{(t-1)})^{p},
\end{align}
where $\alpha,\beta,\gamma,p$ dictate the intensity of influence each dimension exerts on the final aggregation weight. Specifically, $TrustScore$ provides the credibility of the client's execution environment, $ContentScore$ signifies the quality of the current-round update, $HistPerf$ furnishes the memory of long-term contributions, and $RiskEMA$ imposes security constraints as a discount term. This fusion modality guarantees that low-contribution nodes are not instantaneously and permanently eliminated, while ensuring that high-risk nodes are rapidly demoted or isolated, regardless of their high historical contributions.

\begin{algorithm}[htbp]
    \caption{双流正交信任状态演化 (HistPerf \& RiskEMA)}
    \label{alg:phase3}
    \begin{algorithmic}[1]
        \REQUIRE $ContentScore_k$, 多维风险探针集合 $\{r_{probe}, r_{grad}, \dots\}$
        \ENSURE $HistPerf_k^{(t)}$，瞬时风险流 $RiskEMA_k^{(t)}$，全局权值总分 $RawScore_k$
        \STATE \textbf{流 A：历史效用流演化 (基于 Beta 信誉系统)}
        \STATE 计算全局内容得分均值 $\mu_{content}$ 与标准差 $\sigma_{content}$
        \FOR{通过准入的客户端 $k$}
        \STATE 提取正向增益证据 $r_{k}^{good} \leftarrow \mathrm{clip}((ContentScore_k - \mu_{content}) / (\sigma_{content} + \varepsilon), 0, 1)$
        \STATE 提取负向衰减证据 $r_{k}^{bad} \leftarrow 1 - r_{k}^{good}$
        \STATE 更新 Beta 参数 $\alpha_{k}^{(t)} \leftarrow \lambda_h \cdot \alpha_{k}^{(t-1)} + r_{k}^{good}$
        \STATE 更新 Beta 参数 $\beta_{k}^{(t)} \leftarrow \lambda_h \cdot \beta_{k}^{(t-1)} + r_{k}^{bad}$
        \STATE 计算期望效用 $HistPerf_k^{(t)} \leftarrow \alpha_k^{(t)} / (\alpha_k^{(t)} + \beta_k^{(t)} + \varepsilon)$
        \ENDFOR
        \STATE \textbf{流 B：瞬时风险惩戒流演化 (一票否决权)}
        \FOR{每个客户端 $k$}
        \STATE 捕获瞬时风险极值 $Risk_k^{inst} \leftarrow \max\{r_{report}, r_{grad}, r_{probe}, r_{pixel}, r_{trigger}\}$
        \STATE 更新 $RiskEMA_k^{(t)} \leftarrow \beta_r RiskEMA_k^{(t-1)} + (1-\beta_r) Risk_k^{inst}$
        \IF{$RiskEMA_k^{(t)} > \text{隔离门限}$}
        \STATE 加入长期隔离黑名单 $RiskIsolated \leftarrow RiskIsolated \cup \{k\}$
        \ENDIF
        \ENDFOR
        \STATE \textbf{最终权限融合计算}
        \FOR{活跃客户端 $k \notin RiskIsolated$}
        \STATE 融合分数 $RawScore_k \leftarrow (TrustScore_k)^\alpha (ContentScore_k)^\beta (HistPerf_k^{(t-1)})^\gamma$
        \STATE 风险折扣 $RawScore_k \leftarrow RawScore_k \cdot (1 - RiskEMA_k^{(t-1)})^p$
        \ENDFOR
        \RETURN $\{HistPerf_k^{(t)}, RiskEMA_k^{(t)}, RawScore_k\}$
    \end{algorithmic}
\end{algorithm}

**【中文原文】**
\subsection{风险门控驱动的分层聚合}
隐蔽后门往往倾向于潜伏在深层网络参数中。在此情境下，若对全局整网执行无差别聚合，异常更新仍有可能发生跨层透传。针对这一潜在隐患，本文摒弃粗粒度的统一聚合模式，提出一种结合多维风险门控与约束规划思想的分层（Layer-wise）聚合机制（见图~\ref{fig:layer_gating}）。该阶段接收上一阶段输出的 $RawScore_k$，并针对不同网络层分别决定“谁能进入本层聚合、以多大权重参与、其更新幅度是否需要裁剪”。

**【英文翻译】**
\subsection{风险门控驱动的分层聚合}
Stealthy backdoors frequently exhibit a propensity to lie dormant within deep network parameters. In such contexts, executing an indiscriminate aggregation across the entire global network might still permit anomalous updates to penetrate across layers. Addressing this latent hazard, this paper discards the coarse-grained, uniform aggregation paradigm, instead proposing a layer-wise aggregation mechanism synthesizing multi-dimensional risk gating and constrained programming concepts (see Figure~\ref{fig:layer_gating}). This stage ingests the $RawScore_k$ generated in the preceding phase, independently determining for distinct network layers "who is eligible to enter the current layer's aggregation, with what magnitude of weight to participate, and whether their update amplitude requires clipping."

**【中文原文】**
首先，构建\textbf{多维风险门控网络（Risk Gating Network）}以动态感知各个网络层的脆弱性差异。设 $\mathcal{A}$ 为本轮未被软硬隔离的活跃客户端集合（$\mathcal{A} = \{k \mid k \notin RiskIsolated \land k \notin HistSoftIsolated\}$）。对任意网络层 $l$，其综合防御门控敏感度 $S_{total}^{(l)}$ 建模为隐私、效用与安全三个维度的线性组合：
\begin{align}
    S_{privacy}^{(l)}  & = \exp\left(-\tau_{p} \frac{l}{L}\right),                                                                                                          \\
    S_{utility}^{(l)}  & = \frac{\|g_{ref}^{(l)}\|_{2}}{\max_{m}\|g_{ref}^{(m)}\|_{2} + \varepsilon},                                                                       \\
    S_{security}^{(l)} & = 1 - \frac{\sum_{k\in\mathcal{A}}TrustScore_{k}\cdot\cos(\Delta W_{k}^{(l)}, g_{ref}^{(l)})}{\sum_{k\in\mathcal{A}}TrustScore_{k} + \varepsilon}.
\end{align}
基于上述三项指标，经加权合成得到 $S_{total}^{(l)} = w_p S_{privacy}^{(l)} + w_u S_{utility}^{(l)} + w_s S_{security}^{(l)}$。其中，$S_{privacy}^{(l)}$ 描述不同层的隐私暴露敏感性，$S_{utility}^{(l)}$ 反映该层对全局优化方向的贡献强度，$S_{security}^{(l)}$ 则度量该层更新与参考方向的偏离风险。门控网络会根据每一层的实时风险波动，动态输出该层的准入门槛 $\theta^{(l)} = \mu_{base} + \lambda_s \cdot S_{total}^{(l)}$ 以及自适应裁剪边界 $C^{(l)} = C_{base} / (S_{total}^{(l)} + \varepsilon_c)$。当某一层的综合风险升高时，$\theta^{(l)}$ 随之提高，低可信客户端更难进入该层聚合；$C^{(l)}$ 同时收紧，防止高幅值更新对模型参数产生过大牵引。

**【英文翻译】**
First, a \textbf{Multi-Dimensional Risk Gating Network} is constructed to dynamically perceive the varying vulnerabilities across distinct network layers. Let $\mathcal{A}$ represent the set of active clients in the current round that have evaded both soft and hard isolation ($\mathcal{A} = \{k \mid k \notin RiskIsolated \land k \notin HistSoftIsolated\}$). For an arbitrary network layer $l$, its comprehensive defensive gating sensitivity $S_{total}^{(l)}$ is modeled as a linear combination spanning privacy, utility, and security dimensions:
\begin{align}
    S_{privacy}^{(l)}  & = \exp\left(-\tau_{p} \frac{l}{L}\right),                                                                                                          \\
    S_{utility}^{(l)}  & = \frac{\|g_{ref}^{(l)}\|_{2}}{\max_{m}\|g_{ref}^{(m)}\|_{2} + \varepsilon},                                                                       \\
    S_{security}^{(l)} & = 1 - \frac{\sum_{k\in\mathcal{A}}TrustScore_{k}\cdot\cos(\Delta W_{k}^{(l)}, g_{ref}^{(l)})}{\sum_{k\in\mathcal{A}}TrustScore_{k} + \varepsilon}.
\end{align}
Based on these three metrics, the weighted synthesis yields $S_{total}^{(l)} = w_p S_{privacy}^{(l)} + w_u S_{utility}^{(l)} + w_s S_{security}^{(l)}$. Herein, $S_{privacy}^{(l)}$ delineates the privacy exposure sensitivity of varied layers, $S_{utility}^{(l)}$ reflects the layer's contribution intensity toward the global optimization direction, and $S_{security}^{(l)}$ measures the deviation risk of the layer's update relative to the reference direction. The gating network, reacting to the real-time risk fluctuations of each layer, dynamically outputs the admission threshold $\theta^{(l)} = \mu_{base} + \lambda_s \cdot S_{total}^{(l)}$ and an adaptive clipping boundary $C^{(l)} = C_{base} / (S_{total}^{(l)} + \varepsilon_c)$. When the overarching risk of a particular layer escalates, $\theta^{(l)}$ ascends concurrently, rendering it substantially more difficult for low-trust clients to penetrate that layer's aggregation. Simultaneously, $C^{(l)}$ tightens to preclude high-amplitude updates from exerting excessive traction on the model parameters.

**【中文原文】**
其次，引入\textbf{约束规划思想（Optimization Perspective）}执行幸存者权重重归一化。系统排除了 $RawScore_k < \theta^{(l)}$ 的高风险节点后，构建本层的幸存子集 $\Phi^{(l)}$。在此环节中，聚合权重的分配被转化为了一个可信域内的投影优化过程，力求在安全约束内最大化高信誉节点的贡献：
\begin{equation}
    \tilde{w}_{k}^{(l)} = \frac{RawScore_{k}}{\sum_{j\in\Phi^{(l)}}RawScore_{j} + \varepsilon}, \quad \text{s.t.} \sum_{k\in\Phi^{(l)}} \tilde{w}_{k}^{(l)} \approx 1, \tilde{w}_{k}^{(l)} \ge 0.
\end{equation}
该重归一化过程确保被门控保留下来的客户端仍能形成有效聚合权重，避免因部分节点被剔除而导致该层更新幅度失衡。

**【英文翻译】**
Subsequently, an \textbf{Optimization Perspective} is introduced to execute the re-normalization of survivor weights. Having excised the high-risk nodes where $RawScore_k < \theta^{(l)}$, the system formulates the survivor subset $\Phi^{(l)}$ for the current layer. During this procedure, the allocation of aggregation weights transforms into a projection optimization process within a trusted domain, striving to maximize the contributions of highly reputable nodes within security constraints:
\begin{equation}
    \tilde{w}_{k}^{(l)} = \frac{RawScore_{k}}{\sum_{j\in\Phi^{(l)}}RawScore_{j} + \varepsilon}, \quad \text{s.t.} \sum_{k\in\Phi^{(l)}} \tilde{w}_{k}^{(l)} \approx 1, \tilde{w}_{k}^{(l)} \ge 0.
\end{equation}
This re-normalization process guarantees that the clients retained by the gatekeeping mechanism can still establish an effective aggregation weight, effectively averting imbalances in the layer's update magnitude that might otherwise arise from the elimination of certain nodes.

**【中文原文】**
最后，实施\textbf{动态 L2 裁剪与分层组装}。为防止幸存恶意节点在极端方向上拉偏模型，采用缩放算子将偏离预期振幅的更新量强制投影至安全球内，并逐层完成加权聚合：
\begin{equation}
    \widehat{\Delta W}_{k}^{(l)} = \frac{\Delta W_{k}^{(l)}}{\max\left(1, \frac{\|\Delta W_{k}^{(l)}\|_{2}}{C^{(l)}}\right)}, \quad \Delta W_{global}^{(l)} = \sum_{k\in\Phi^{(l)}}\tilde{w}_{k}^{(l)} \cdot \widehat{\Delta W}_{k}^{(l)}.
\end{equation}

**【英文翻译】**
Finally, the framework enforces \textbf{Dynamic L2 Clipping and Layered Assembly}. To prevent surviving malicious nodes from skewing the model toward extreme directions, a scaling operator is deployed to forcibly project update quantities that deviate from anticipated amplitudes back into a secure sphere, culminating in the layer-wise weighted aggregation:
\begin{equation}
    \widehat{\Delta W}_{k}^{(l)} = \frac{\Delta W_{k}^{(l)}}{\max\left(1, \frac{\|\Delta W_{k}^{(l)}\|_{2}}{C^{(l)}}\right)}, \quad \Delta W_{global}^{(l)} = \sum_{k\in\Phi^{(l)}}\tilde{w}_{k}^{(l)} \cdot \widehat{\Delta W}_{k}^{(l)}.
\end{equation}

**【中文原文】**
为说明该机制的实际运作逻辑，可以考察一个隐蔽后门植入案例。假设攻击者试图在网络深层的全连接层嵌入语义触发器；由于恶意更新偏离正常分布，安全敏感度 $S_{security}^{(l)}$ 会明显升高。此时门控网络从两个方向介入：一方面抬高信誉门槛 $\theta^{(l)}$，使低 $RawScore$ 节点无法进入该层聚合；另一方面缩小 $C^{(l)}$，限制幸存更新的参数范数。浅层特征提取层若风险较低，则可保留相对宽松的门槛与裁剪边界。通过这种层级差异化控制，系统能够削弱深层后门特征向全局模型的渗透，同时减少对合法浅层通用特征的过度压制。

**【英文翻译】**
To illustrate the practical operational logic of this mechanism, consider the case of stealthy backdoor implantation. Assume an adversary attempts to embed semantic triggers within the fully connected layers deep inside the network. Because the malicious updates diverge from the normal distribution, the security sensitivity $S_{security}^{(l)}$ will markedly elevate. At this juncture, the gating network intervenes from two directions. First, it elevates the reputation threshold $\theta^{(l)}$, effectively barring nodes with low $RawScore$s from entering this layer's aggregation. Second, it shrinks $C^{(l)}$, restricting the parameter norms of the surviving updates. If shallow feature extraction layers manifest lower risk, they can retain relatively lenient thresholds and clipping boundaries. Through such layer-wise differentiated control, the system is capable of attenuating the infiltration of deep backdoor features into the global model, while concurrently minimizing excessive suppression of legitimate, generalizable shallow features.

\begin{figure}[htbp]
    \centering
    \includegraphics[width=0.95\textwidth]{fig5_layer.pdf}
    \caption{风险门控驱动的分层自适应审查与动态裁剪机制示意图}
    \label{fig:layer_gating}
\end{figure}

\begin{algorithm}[htbp]
    \caption{基于风险门控的分层差异化聚合与动态裁剪}
    \label{alg:phase4}
    \begin{algorithmic}[1]
        \REQUIRE 活跃节点 $\mathcal{A}$，分数 $RawScore_k$，分层更新梯度 $\{\Delta W_k^{(l)}\}$，网络深度 $L$
        \ENSURE 本轮全局安全梯度 $\Delta W_{global}$
        \STATE 初始化全局增量 $\Delta W_{global} \leftarrow 0$
        \FOR{网络每一层 $l = 1, 2, \dots, L$}
        \STATE \textbf{步骤 1: 层级敏感度三维联合测算}
        \STATE 隐私敏感度 $S_{privacy}^{(l)} \leftarrow \exp(-\tau_p \cdot l/L)$
        \STATE 效用敏感度 $S_{utility}^{(l)} \leftarrow \|g_{ref}^{(l)}\|_2 / \max_m\|g_{ref}^{(m)}\|_2$
        \STATE 安全敏感度 $S_{security}^{(l)} \leftarrow 1 - \frac{\sum_{k\in\mathcal{A}} TrustScore_k \cos(\Delta W_k^{(l)}, g_{ref}^{(l)})}{\sum_{k\in\mathcal{A}} TrustScore_k + \varepsilon}$
        \STATE 总防御诉求敏感度 $S_{total}^{(l)} \leftarrow w_p S_{privacy}^{(l)} + w_u S_{utility}^{(l)} + w_s S_{security}^{(l)}$
        \STATE \textbf{步骤 2: 动态风险门控与 L2 自适应裁剪}
        \STATE 提高本层安全入场分数门槛 $\theta^{(l)} \leftarrow \mu_{base} + \lambda_s \cdot S_{total}^{(l)}$
        \STATE 收紧本层恶意振幅裁剪边界 $C^{(l)} \leftarrow C_{base} / (S_{total}^{(l)} + \varepsilon_c)$
        \STATE \textbf{步骤 3: 幸存节点挑选与二次重校准}
        \STATE 筛选本层幸存者名单 $\Phi^{(l)} \leftarrow \{k \in \mathcal{A} \mid RawScore_k \ge \theta^{(l)}\}$
        \STATE 对幸存者重新归一化有效权重 $\tilde{w}_k^{(l)} \leftarrow RawScore_k / \sum_{j\in\Phi^{(l)}} RawScore_j$
        \STATE 按规则执行 L2 等比缩小 $\widehat{\Delta W}_k^{(l)} \leftarrow \Delta W_k^{(l)} / \max(1, \|\Delta W_k^{(l)}\|_2 / C^{(l)})$
        \STATE \textbf{步骤 4: 分层合并拼接}
        \STATE 计算本层安全聚合增量 $\Delta W_{global}^{(l)} \leftarrow \sum_{k\in\Phi^{(l)}} \tilde{w}_k^{(l)} \cdot \widehat{\Delta W}_k^{(l)}$
        \STATE 拼接并写入全局模型更新量 $\Delta W_{global} \leftarrow \Delta W_{global} \cup \Delta W_{global}^{(l)}$
        \ENDFOR
        \RETURN $\Delta W_{global}$
    \end{algorithmic}
\end{algorithm}

**【中文原文】**
\subsection{模型更新下发与知识留存}
分层聚合完成后，服务器将安全增量应用到全局模型：$W_{global}^{new} = W_{global}^{old} + \Delta W_{global}$，并同步下发更新后的模型及客户端状态（含 $HistPerf$）。至此形成一轮完整闭环，在保证收敛的同时持续过滤恶意更新。

**【英文翻译】**
\subsection{模型更新下发与知识留存}
Upon the completion of layered aggregation, the server applies the secure increment to the global model: $W_{global}^{new} = W_{global}^{old} + \Delta W_{global}$, and synchronously distributes the updated model along with the clients' states (including $HistPerf$). This culminates in a complete closed loop, ensuring convergence while relentlessly filtering out malicious updates.

**【中文原文】**
\subsection{双流正交解耦的理论保证 (Theoretical Analysis)}
传统单一信誉分数（如简单余弦累加）本质上将高维行为压缩到单轴判断。在强 Non-IID 场景下，这会使得漏检（FNR）与误杀（FPR）的冲突加剧。本节给出双流正交机制的理论分析。

**【英文翻译】**
\subsection{双流正交解耦的理论保证 (Theoretical Analysis)}
Traditional single reputation scores (such as simple cosine accumulation) inherently compress high-dimensional behaviors into single-axis judgments. Under formidable Non-IID scenarios, this invariably exacerbates the conflict between false negative rates (FNR) and false positive rates (FPR). This section articulates the theoretical analysis of the dual-stream orthogonal mechanism.

**【中文原文】**
\textbf{引理 1（长尾节点的方差收敛特性，Lemma 1）}
设长尾合法客户端 $k$ 的单轮内容分 $ContentScore_{k}^{(t)}$ 服从期望 $\mu_{clean}$、方差 $\sigma_{clean}^2$ 的扰动分布。在刚性阈值 $\tau_{hard}$ 下，若 $\tau_{hard} > \mu_{clean} - \sigma_{clean}$，该节点将有较高概率被持续淘汰。采用历史效用流平滑后，其稳态期望满足 $\mathbb{E}[HistPerf_k^{(\infty)}] = \mu_{clean}$，且方差收敛为：
\begin{equation}
    \operatorname{Var}(HistPerf_{k}^{(\infty)}) = \frac{1-\beta_h}{1+\beta_h} \sigma_{clean}^{2}
\end{equation}
由于 $0 < \beta_h < 1$，当 $\beta_h \to 1$ 时，短时扰动被显著平滑。只要 $\mu_{clean}$ 高于生存阈值，历史效用流可作为低通滤波器提高合法节点长期存活概率，理论上支持 $\lim_{t \to \infty} \text{FPR} = 0$。

**【英文翻译】**
\textbf{Lemma 1 (Variance Convergence Property of Long-Tail Nodes)}
Assume that the single-round content score $ContentScore_{k}^{(t)}$ of a legitimate long-tail client $k$ follows a perturbed distribution with expectation $\mu_{clean}$ and variance $\sigma_{clean}^2$. Under a rigid threshold $\tau_{hard}$, if $\tau_{hard} > \mu_{clean} - \sigma_{clean}$, this node faces a high probability of sustained elimination. Upon adopting the historical utility stream for smoothing, its steady-state expectation satisfies $\mathbb{E}[HistPerf_k^{(\infty)}] = \mu_{clean}$, and the variance converges to:
\begin{equation}
    \operatorname{Var}(HistPerf_{k}^{(\infty)}) = \frac{1-\beta_h}{1+\beta_h} \sigma_{clean}^{2}
\end{equation}
Given that $0 < \beta_h < 1$, as $\beta_h \to 1$, short-term perturbations are markedly smoothed. As long as $\mu_{clean}$ exceeds the survival threshold, the historical utility stream functions as a low-pass filter, enhancing the long-term survival probability of legitimate nodes and theoretically supporting $\lim_{t \to \infty} \text{FPR} = 0$.

**【中文原文】**
\textbf{引理 2（高阶潜伏投毒的瞬时冲激响应，Lemma 2）}
对“长期伪装、间歇爆发”的后门节点 $m$，即使其前期累积了较高 $HistPerf$，在攻击轮次仍会触发异常探针峰值（$\exists r \in \{r_{grad}, r_{probe}, r_{trigger}\}, r \gg 1$）。由于 $Risk_k^{inst}$ 取多探针最大值，且 EMA 对输入单调，RiskEMA 轨迹满足下界：
\begin{equation}
    RiskEMA_m^{(t)} \ge \max \left( \beta_r \cdot RiskEMA_m^{(t-1)},\ \mathcal{F}_{probe}(r_{grad}, r_{probe}, r_{trigger}) \right)
\end{equation}
当 $\mathcal{F}_{probe}$ 触发异常突变时，风险值会在短时间内跃升并逼近或超过门限，从而触发隔离。

**【英文翻译】**
\textbf{Lemma 2 (Instantaneous Impulse Response to High-Order Sleeper Poisoning)}
Regarding a backdoor node $m$ executing a strategy of "long-term camouflage followed by intermittent bursts," even if it has accrued a high $HistPerf$ during early stages, it will invariably trigger an abnormal probe peak during the attack round ($\exists r \in \{r_{grad}, r_{probe}, r_{trigger}\}, r \gg 1$). Because $Risk_k^{inst}$ seizes the maximum value across multiple probes, and the EMA maintains monotonicity concerning the input, the RiskEMA trajectory satisfies the following lower bound:
\begin{equation}
    RiskEMA_m^{(t)} \ge \max \left( \beta_r \cdot RiskEMA_m^{(t-1)},\ \mathcal{F}_{probe}(r_{grad}, r_{probe}, r_{trigger}) \right)
\end{equation}
When $\mathcal{F}_{probe}$ activates an anomalous mutation, the risk value surges rapidly, approaching or breaching the threshold within a brief timeframe, thereby triggering isolation.

**【中文原文】**
\textbf{定理 1（双流熔断正交解耦，Theorem 1）}
\textit{在双流机制下，诚实长尾节点的高方差更新由 $HistPerf$ 通道平滑吸收；恶意攻击的突发行为则由 $Risk^{inst}$ 通道快速放大并触发熔断。两类信号在判别空间中被解耦处理，从而缓解单分数机制难以同时优化 $\text{FPR}$ 与 $\text{ASR}$ 的矛盾。}

**【英文翻译】**
\textbf{Theorem 1 (Dual-Stream Circuit Breaking and Orthogonal Decoupling)}
\textit{Under the dual-stream mechanism, the high-variance updates of honest long-tail nodes are smoothly absorbed by the $HistPerf$ channel. Conversely, the abrupt behaviors characteristic of malicious attacks are swiftly amplified by the $Risk^{inst}$ channel, triggering an immediate circuit break. These two categories of signals are decoupled and processed within distinct discriminative spaces, thereby alleviating the profound paradox wherein single-score mechanisms struggle to simultaneously optimize both FPR and ASR.}


**【中文原文】**
\section{实验与分析}
\label{sec:experiments}
\subsection{实验设置与可复现参数}

\subsubsection{基准环境与系统软硬件栈}
实验基于 Flower (1.5.0) 与 PyTorch 实现。所有仿真均部署在一台 Inspur 服务器上，硬件配置为双路 CPU + 5 块 NVIDIA A10 (24GB) GPU，软件环境为 Ubuntu 20.04.6 LTS 与 CUDA 12.8。

为保证可复现性，本文保留了完整日志、代码与启动脚本。需要说明的是：节点状态轨迹图（如图~\ref{fig:node_state}）来自固定随机种子（如 \texttt{seed=42}）的一次代表性运行；Acc、ASR 等总体指标则采用 5 次独立随机种子实验的均值统计。

**【英文翻译】**
\section{实验与分析}
\label{sec:experiments}
\subsection{实验设置与可复现参数}

\subsubsection{基准环境与系统软硬件栈}
The experiments are implemented utilizing Flower (1.5.0) and PyTorch. All simulations are deployed on an Inspur server equipped with dual CPUs and five NVIDIA A10 (24GB) GPUs. The software environment consists of Ubuntu 20.04.6 LTS and CUDA 12.8.

To guarantee reproducibility, this study preserves complete logs, source codes, and startup scripts. It is pertinent to note that the node state trajectory charts (e.g., Figure~\ref{fig:node_state}) are derived from a single representative execution employing a fixed random seed (such as \texttt{seed=42}). Conversely, overarching metrics—including Accuracy (Acc) and Attack Success Rate (ASR)—are formulated through the statistical averaging of five independent experiments executed with varying random seeds.

**【中文原文】**
\subsubsection{数据集异构划分方式}
模型使用轻量级卷积神经网络，数据集为 CIFAR-10。为构造 Non-IID 环境，50000 张训练图像按以下方式划分：
\begin{itemize}
    \item \textbf{共享基础池}：抽取 5000 个类别均衡样本供所有合法节点共享，用于基础对齐。
    \item \textbf{弱异构群（Group A, 节点 6-11）}：Dirichlet($\alpha=1.0$)，模拟中等程度分布偏斜。
    \item \textbf{强长尾异构群（Group B \& C, 节点 12-19）}：Dirichlet($\alpha=0.1$)，客户端类别分布高度偏斜，更易被传统余弦机制误判。
\end{itemize}

**【英文翻译】**
\subsubsection{数据集异构划分方式}
The model adopts a lightweight convolutional neural network, with the dataset designated as CIFAR-10. To engineer a Non-IID environment, the 50,000 training images are partitioned as follows:
\begin{itemize}
    \item \textbf{Shared Base Pool}: A subset of 5,000 class-balanced samples is extracted and shared among all legitimate nodes to facilitate foundational alignment.
    \item \textbf{Weakly Heterogeneous Group (Group A, Nodes 6-11)}: Governed by a Dirichlet distribution ($\alpha=1.0$), simulating a moderate degree of distributional skew.
    \item \textbf{Strong Long-Tail Heterogeneous Group (Group B \& C, Nodes 12-19)}: Governed by a Dirichlet distribution ($\alpha=0.1$), where the client class distributions are acutely skewed, thereby significantly increasing their vulnerability to misclassification by traditional cosine mechanisms.
\end{itemize}

**【中文原文】**
\subsubsection{恶意攻击实例与比例}
为评估框架在复杂威胁下的识别能力，实验在 20 个节点中注入 6 个恶意节点（占比 30\%），覆盖数据投毒与参数操纵两类攻击：
\begin{itemize}
    \item \textbf{Client 0 - 标签翻转（Label Flip, $\gamma=0.5$）}：将部分样本标签映射到错误类别。
    \item \textbf{Client 1 - 触发器后门（Backdoor, $\gamma=0.2$）}：在 20\% 样本中加入触发器并定向标记为目标类 $0$。
    \item \textbf{Client 2 - 干净标签后门（Clean Label, $\gamma=0.5$）}：扰动目标类输入但保持标签不变，提升隐蔽性。
    \item \textbf{Client 3 - 语义后门（Semantic, $\gamma=0.5$）}：利用自然语义偏置诱导错误关联。
    \item \textbf{Client 4 - 符号翻转（Sign-Flipping）}：对回传梯度执行符号反转（$\Delta \widehat{W}_k = - \gamma \cdot \Delta W_k$）。
    \item \textbf{Client 5 - 梯度缩放（Gradient Scaling）}：将恶意增量放大 100 倍（$\Delta \widehat{W}_k = 100 \times \Delta W_k$）。
    \item \textbf{女巫与搭便车节点（Sybil \& Free-rider）}：额外注入 5 个无有效 TEE 证书节点与 3 个伪造低负载节点，用于验证阶段一硬件门禁。
\end{itemize}

**【英文翻译】**
\subsubsection{恶意攻击实例与比例}
To evaluate the framework's identification capacity amid complex threats, the experiment injects 6 malicious nodes into a pool of 20 nodes (constituting 30\%), encompassing two primary attack paradigms: data poisoning and parameter manipulation:
\begin{itemize}
    \item \textbf{Client 0 - Label Flip ($\gamma=0.5$)}: Maps a proportion of sample labels to erroneous classes.
    \item \textbf{Client 1 - Trigger Backdoor ($\gamma=0.2$)}: Embeds a trigger into 20\% of the samples, deliberately targeting and labeling them as class $0$.
    \item \textbf{Client 2 - Clean Label Backdoor ($\gamma=0.5$)}: Perturbs inputs of the target class while preserving the original labels, substantially augmenting stealthiness.
    \item \textbf{Client 3 - Semantic Backdoor ($\gamma=0.5$)}: Exploits natural semantic biases to induce fallacious associations.
    \item \textbf{Client 4 - Sign-Flipping}: Executes a sign inversion on the returned gradients ($\Delta \widehat{W}_k = - \gamma \cdot \Delta W_k$).
    \item \textbf{Client 5 - Gradient Scaling}: Amplifies the malicious increments by a factor of 100 ($\Delta \widehat{W}_k = 100 \times \Delta W_k$).
    \item \textbf{Sybil \& Free-rider Nodes}: Five additional nodes devoid of valid TEE certificates and three nodes simulating forged low workloads are injected explicitly to validate the hardware gating mechanism in Phase One.
\end{itemize}

**【中文原文】**
\textbf{前置拦截说明}：上述 8 个外部渗透或资源欺诈节点均在协议阶段被拦截，要么未通过 TMAA 硬件门禁（$M_{attest,k}=0$），要么因异常行为导致 $TrustScore_k \to 0$。因此，后续统计的 20 个节点均为通过阶段一准入后的正式参与者。

实验使用的全局超参数与防御组件配置见表~\ref{tab:hyperparams}。

**【英文翻译】**
\textbf{Preemptive Interception Clarification}: The aforementioned eight external infiltration or resource fraud nodes are uniformly intercepted during the protocol phase. They either fail the TMAA hardware gating ($M_{attest,k}=0$) or see their $TrustScore_k \to 0$ owing to anomalous behaviors. Consequently, the 20 nodes statistically analyzed in subsequent sections represent the official participants that successfully navigated the Phase One admission.

The global hyperparameters and defensive component configurations employed in the experiment are delineated in Table~\ref{tab:hyperparams}.

\begin{table}[htbp]
    \centering
    \caption{基于物理平台的联邦仿真全局超参数与防御组件配置}
    \label{tab:hyperparams}
    \begin{tabular}{p{4cm} p{8.5cm} p{2cm}}
        \toprule
        \textbf{模块架构归属}                              & \textbf{防御组件超参数含义与控制作用简述}                         & \textbf{实验组取值}  \\
        \midrule
        \multirow{2}{*}{\textbf{基础环境与演化轮次}}       & 强长尾异构通讯拓扑节点总量 ($K$)                                  & $20$ 节点            \\
                                                           & 本地训练 SGD 优化起步参数 ($lr$, $Momentum$)                      & $0.001$, $0.9$       \\
        \midrule
        \multirow{3}{*}{\textbf{双流协同：阶段 1 $\to$ 3}} & TMAA 基准罚时陡峭度 $\lambda$，死区 $\tau$，衰减指数 $\rho$       & $5.0$, $0.1$, $2.0$  \\
                                                           & 二维协同审查常量约束映射 $\alpha_1, \alpha_2$ 及 $\beta_{fusion}$ & $0.6$, $0.4$, $2.0$  \\
                                                           & 历史留存平滑阈值 $\beta_h$ 与瞬发风险半衰期 $\beta_r$             & $0.9$, $0.85$        \\
        \midrule
        \multirow{2}{*}{\textbf{逐层裁剪：阶段 4}}         & 得分融合非线性指数调和阀 ($\alpha, \beta, \gamma, p$)             & $3.0, 1.0, 0.5, 1.0$ \\
                                                           & 门槛拦截控制下界 $\mu_{base}$ 及惩戒放大基线 $\lambda_s$          & $0.4$, $1.2$         \\
        \bottomrule
    \end{tabular}
\end{table}

**【中文原文】**
\textbf{运行说明}：正式实验执行 30 轮联邦训练，每轮本地训练 3 个 Epoch。轨迹图和单次耗时（3878.53 s）来自真实 \texttt{server.log}；准确率类指标报告 5 次重复实验均值，未做插值平滑。

\subsection{防御效果实证分析}

\subsubsection{全局收敛性与攻击防范表现}
如图~\ref{fig:convergence} 所示，在 30\% 恶意占比下，模型精度稳定收敛至 92.31\%，后门 ASR 降至 10.21\%。

**【英文翻译】**
\textbf{Execution Details}: The formal experiment executes 30 rounds of federated training, with each round comprising 3 local Epochs. The trajectory charts and single-run duration (3878.53 s) are extracted from the authentic \texttt{server.log}. Metrics pertaining to accuracy report the mean of 5 replicated experiments, devoid of any interpolation smoothing.

\subsection{防御效果实证分析}

\subsubsection{全局收敛性与攻击防范表现}
As illustrated in Figure~\ref{fig:convergence}, under a 30\% malicious proportion, the model accuracy converges steadily to 92.31\%, while the backdoor ASR plummets to 10.21\%.

\begin{figure}[htbp]
    \centering
    \includegraphics[width=0.85\textwidth]{fig6_convergence_asr.pdf}
    \caption{全局收敛准确率 (Accuracy) 与后门攻击成功率 (ASR) 演化曲线}
    \label{fig:convergence}
\end{figure}

**【中文原文】**
\textbf{统计可靠性说明}：本节及后续全局指标（Acc、ASR 等）均来自 5 次重复实验均值；节点轨迹图来自单次代表性运行。

\textbf{50\% 恶意占比边界测试}：为验证第 3.2 节假设上限（恶意占比 $<50\%$）附近的行为，本文额外构建 \textit{Flwr-half} 1:1 对抗环境（10 恶意 + 10 合法，覆盖全部 6 类攻击）。结果见表~\ref{tab:half_malicious}。

**【英文翻译】**
\textbf{Statistical Reliability Clarification}: This section and subsequent overarching metrics (e.g., Acc, ASR) are uniformly derived from the mean of 5 repeated experiments. The node trajectory charts originate from a single representative run.

\textbf{50\% Malicious Proportion Boundary Testing}: To empirically validate the behavioral characteristics near the theoretical upper bound (malicious proportion $<50\%$) hypothesized in Section 3.2, this study constructs an auxiliary \textit{Flwr-half} 1:1 adversarial environment (10 malicious vs. 10 legitimate nodes, encompassing all 6 attack categories). The outcomes are detailed in Table~\ref{tab:half_malicious}.

\begin{table}[htbp]
    \centering
    \caption{\textbf{50\% 恶意占比极限压力测试与标准 30\% 基线的对比}}
    \vspace{4pt}
    \label{tab:half_malicious}
    \begin{tabular}{l c c c c}
        \toprule
        \textbf{实验设置}                    & \textbf{Acc (\%)}         & \textbf{ASR (\%)}         & \textbf{TPR (\%)} & \textbf{FPR (\%)} \\
        \midrule
        标准基线 (30\% 恶意, 6/20)           & 92.31 $\pm 0.09$          & 10.21 $\pm 0.05$          & 100               & 0.00              \\
        \textbf{极限测试 (50\% 恶意, 10/20)} & \textbf{91.81 $\pm 0.10$} & \textbf{10.46 $\pm 0.06$} & \textbf{100}      & \textbf{0.00}     \\
        \bottomrule
    \end{tabular}
\end{table}

**【中文原文】**
如表所示，在接近理论边界的强对抗环境下，框架仍保持 91.81\% 的准确率，ASR 为 10.46\%（接近随机猜测基线 10\%）。10 个恶意节点全部被识别并剔除（TPR=100\%），10 个合法节点无永久误封（FPR=0\%）。此外，30 轮日志显示测试集 Loss 从 $0.06362$ 下降至 $0.00883$，说明模型在防御条件下仍保持稳定收敛。

\subsubsection{信任流追溯与恶意节点封禁剖析}
信任流机制的关键在于“及时暴露恶意节点”和“分级处置风险”。图~\ref{fig:node_state} 为避免曲线混乱，仅展示 4 个代表性节点：Client 4（早期参数篡改）、Client 0（高频显性投毒）、Client 2（隐蔽潜伏后门）和合法长尾节点 Client 15。其判定过程如下：
\begin{itemize}
    \item \textbf{Client 0（Label Flip）与 Client 1（Backdoor）}：两者在 $r_{grad}$ 与 $r_{probe}$ 上持续高风险，至第 8 轮触发 $\texttt{risk\_ema\_above\_0.90\_for\_4\_rounds}$，进入黑名单。
    \item \textbf{Client 3（Semantic）}：像素扰动不明显，但长期偏离纯净参考 $g_{root\_clean}$。其先进入软隔离，随后触发 $\texttt{risk\_soft\_isolation\_for\_8\_rounds}$，第 16 轮被移除。
    \item \textbf{Client 2（Clean Label）}：本地 Loss 表面正常，但长期漂移特征被连击规则命中（$\texttt{c2\_drift\_combo\_for\_5\_rounds}$），第 24 轮完成识别与剔除。
    \item \textbf{Client 4（Sign-Flipping）与 Client 5（Gradient Scaling）}：前者因方向反转导致 $S_{contrib}$ 迅速降为低值并触发硬封禁；后者因超大振幅命中分层 L2 门控后进入异常处置并被剔除。
\end{itemize}
结果表明，双流解耦机制能够将“数据异构导致的低分”与“真实攻击行为”分开处理。在包含 6 个恶意节点的设置下，系统达到 \textbf{TPR=100\%}。

**【英文翻译】**
As demonstrated in the table, under the intense adversarial environment approaching the theoretical boundary, the framework sustains an accuracy of 91.81\%, alongside an ASR of 10.46\% (proximate to the random guess baseline of 10\%). All 10 malicious nodes are successfully identified and excised (TPR=100\%), while none of the 10 legitimate nodes suffer permanent erroneous bans (FPR=0\%). Furthermore, the 30-round log indicates a reduction in the test set Loss from $0.06362$ to $0.00883$, unequivocally proving that the model maintains stable convergence even under stringent defensive constraints.

\subsubsection{信任流追溯与恶意节点封禁剖析}
The crux of the trust flow mechanism lies in the "prompt exposure of malicious nodes" and the "hierarchical management of risks." To avert visual clutter, Figure~\ref{fig:node_state} solely illustrates four representative nodes: Client 4 (early-stage parameter tampering), Client 0 (high-frequency explicit poisoning), Client 2 (concealed sleeper backdoor), and the legitimate long-tail Client 15. Their adjudication processes unfold as follows:
\begin{itemize}
    \item \textbf{Client 0 (Label Flip) \& Client 1 (Backdoor)}: Both exhibit sustained high risk on $r_{grad}$ and $r_{probe}$, ultimately triggering $\texttt{risk\_ema\_above\_0.90\_for\_4\_rounds}$ at round 8, thereby entering the blacklist.
    \item \textbf{Client 3 (Semantic)}: Despite inconspicuous pixel perturbations, it chronically deviates from the clean reference $g_{root\_clean}$. It initially enters soft isolation, subsequently triggering $\texttt{risk\_soft\_isolation\_for\_8\_rounds}$, culminating in removal at round 16.
    \item \textbf{Client 2 (Clean Label)}: Although the local Loss appears superficially normal, its protracted drift features are captured by the combo rule ($\texttt{c2\_drift\_combo\_for\_5\_rounds}$), achieving identification and expulsion by round 24.
    \item \textbf{Client 4 (Sign-Flipping) \& Client 5 (Gradient Scaling)}: The former precipitates a precipitous drop in $S_{contrib}$ due to directional inversion, triggering a hard ban. The latter, characterized by extreme amplitude, encounters the layered L2 gating, enters anomaly processing, and is consequently excised.
\end{itemize}
The outcomes confirm that the dual-stream decoupling mechanism effectively isolates "low scores induced by data heterogeneity" from "authentic attack behaviors." Within the configuration harboring 6 malicious nodes, the system achieves a \textbf{TPR=100\%}.

\begin{figure}[htbp]
    \centering
    \includegraphics[width=0.85\textwidth]{fig7_node_state_evolution.pdf}
    \caption{扩展混合攻击下核心节点信任与风险状态时序追踪}
    \label{fig:node_state}
\end{figure}

**【中文原文】**
\subsubsection{异构长尾节点的误杀保障 (FPR 指标分析)}
传统距离型方法（如 Krum\cite{blanchard2017krum}、FLTrust\cite{cao2021fltrust}）在 Dirichlet $\alpha=0.1$ 的强异构环境中容易误判合法长尾节点。本文实验显示：\textbf{30 轮训练中所有合法节点均未触发永久封禁，FPR=0\%。}
即使早期部分合法节点（如 Client 15）因数据偏斜出现较低 $ContentScore$ 并进入 SUSPECT/QUARANTINE，其 $RiskEMA$ 未持续升高，故仅会受到临时准入限制与分层裁剪。随着后续贡献恢复，$HistPerf$ 可逐步回升，最终合法节点留存率为 100\%。

为进一步解释“低误杀”现象，本文提取干预前后的节点特征并用 t-SNE 可视化。图~\ref{fig:tsne_manifold} 显示，双流机制可将恶意簇与合法长尾簇有效分离，同时保留合法异构节点在主聚合区域内。

**【英文翻译】**
\subsubsection{异构长尾节点的误杀保障 (FPR 指标分析)}
Traditional distance-centric methods (such as Krum\cite{blanchard2017krum} and FLTrust\cite{cao2021fltrust}) are highly susceptible to misjudging legitimate long-tail nodes within strongly heterogeneous environments characterized by Dirichlet $\alpha=0.1$. Experiments conducted in this study reveal: \textbf{Across the 30-round training, zero legitimate nodes trigger a permanent ban, cementing an FPR=0\%.}
Even if certain legitimate nodes (e.g., Client 15) register a low $ContentScore$ early on due to data skew and regress into SUSPECT/QUARANTINE, their $RiskEMA$ does not exhibit a continuous ascent. Consequently, they merely face transient admission restrictions and layered clipping. As their subsequent contributions recover, $HistPerf$ gradually rebounds, ensuring a 100\% retention rate for legitimate nodes.

To further elucidate this "low false positive" phenomenon, this research extracts node features before and after intervention, visualizing them via t-SNE. Figure~\ref{fig:tsne_manifold} exhibits that the dual-stream mechanism effectively disentangles the malicious clusters from the legitimate long-tail clusters, simultaneously anchoring the legitimate heterogeneous nodes within the principal aggregation domain.

\begin{figure}[htbp]
    \centering
    \includegraphics[width=0.9\textwidth]{fig8_tsne_visualization.pdf}
    \caption{联邦参与节点特征向量在双流防御前后的 t-SNE 降维对比}
    \label{fig:tsne_manifold}
\end{figure}

**【中文原文】**
\subsection{防御机制横向基准对比 (Baseline Comparison)}
\textbf{公平性说明}：所有基线均在与本文完全相同的联邦设置下运行，包括节点划分（20 个）、数据异构度（Dirichlet $\alpha=0.1$）、攻击配置（30\% 混合攻击）、初始化参数、优化器设置（$lr=0.001$, $momentum=0.9$）和通信轮次。

在统一环境下，本文将所提方法与四类经典鲁棒聚合方法进行横向比较：

\textbf{FedAvg}\cite{mcmahan2017fedavg} 作为无防御基线，反映模型在受攻击时的退化程度；\textbf{Krum}\cite{blanchard2017krum} 通过最小欧氏距离选择单个代表更新；\textbf{Trimmed Mean}\cite{yin2018byzantine} 在坐标维度执行截断均值；\textbf{FLTrust}\cite{cao2021fltrust} 借助服务器小规模干净集构造参考向量并按余弦相似度加权。

各方法在该高风险场景下的量化结果见表~\ref{tab:baseline}。

**【英文翻译】**
\subsection{防御机制横向基准对比 (Baseline Comparison)}
\textbf{Fairness Statement}: All baselines are executed under the identical federated configuration as this paper. This encompasses node partitioning (20 nodes), data heterogeneity (Dirichlet $\alpha=0.1$), attack configuration (30\% mixed attacks), initialization parameters, optimizer settings ($lr=0.001$, $momentum=0.9$), and communication rounds.

Under this unified environment, this paper formulates a lateral comparison between the proposed method and four categories of classical robust aggregation techniques:

\textbf{FedAvg}\cite{mcmahan2017fedavg} serves as the defenseless baseline, mirroring the degree of model degradation when subjected to attacks; \textbf{Krum}\cite{blanchard2017krum} selects a singular representative update via minimal Euclidean distance; \textbf{Trimmed Mean}\cite{yin2018byzantine} executes truncated averaging across coordinate dimensions; \textbf{FLTrust}\cite{cao2021fltrust} leverages a small-scale clean set on the server to construct a reference vector, applying weighting based on cosine similarity.

The quantitative outcomes of each method in this high-risk scenario are documented in Table~\ref{tab:baseline}.

\begin{table}[htbp]
    \centering
    \begin{threeparttable}
        \caption{不同联邦学习防御策略在 30\% 高危混合攻击环境下的性能对比}
        \vspace{4pt}
        \label{tab:baseline}
        \begin{tabular}{l l c c c}
            \toprule
            \textbf{防御策略}                    & \textbf{核心机制分类}      & \textbf{\shortstack{全局准确率 $\mu \pm \sigma$                                               \\ (Acc. \%)}} & \textbf{\shortstack{攻击成功率 $\mu \pm \sigma$\\ (ASR \%)}} & \textbf{\shortstack{正常节点误杀率 $\mu$\\ (FPR \%)}} \\
            \midrule
            FedAvg \cite{mcmahan2017fedavg}      & 无防御基线                 & 86.15 $\pm 1.2$                                 & 92.34 $\pm 5.1$           & N/A ($*$)       \\
            Krum \cite{blanchard2017krum}        & 基于欧氏距离               & 64.20 $\pm 2.8$                                 & 12.15 $\pm 0.9$           & 64.20 ($^{**}$) \\
            Trimmed Mean \cite{yin2018byzantine} & 坐标轴独立裁剪             & 71.35 $\pm 2.4$                                 & 38.60 $\pm 4.2$           & N/A ($*$)       \\
            FLTrust \cite{cao2021fltrust}        & 单向信任锚点               & 81.25 $\pm 1.5$                                 & 15.42 $\pm 1.1$           & 21.40 ($^{**}$) \\
            \textbf{本文框架 (Trust Flow)}       & \textbf{双流解耦+层级裁剪} & \textbf{92.31 $\pm 0.09$}                       & \textbf{10.21 $\pm 0.05$} & \textbf{0.00}   \\
            \bottomrule
        \end{tabular}
        \begin{tablenotes}
            \small
            \item (*) \textit{注：FedAvg 与 Trimmed Mean 算法由于自身不具备任何客户端“显式信任评估”或“永久拉黑剔除 (Ban)”机制，其对恶意节点的容忍表现为数值融合或截断计算，因此 FPR 指标不适用于此类算法，标记为 N/A。}
            \item (**) \textit{注：正常节点误杀率（FPR）这一指标受确定性规则与固化数据样本异构度（Dirichlet分布）的强约束。在固定的数据集切分下，由于防御规则是确定性的，该类误杀裁决在各次重复实验中观测到方差极小，因此本列表仅呈报该指标稳定收敛的标量期望均值 $\mu$。同时，此处的 0.00 专指“永久封禁误杀”，部分处于瞬时可疑池中的轻度隔离由于具有触底恢复反弹特性，不计入模型不可挽回的实质性永久击溃错误。}
        \end{tablenotes}
    \end{threeparttable}
\end{table}

**【中文原文】**
结果显示：FedAvg 在混合攻击下 ASR 高达 92.34\%；Krum 可将 ASR 降至 12.15\%，但 FPR 升至 64.2\%，准确率降至 64.20\%。相比之下，本文方法在保持 FPR=0\% 的同时取得最高准确率 92.31\%，并实现最低 ASR（10.21\%）。基于多次重复实验的 Student's $t$-test 显示，相比强基线（如 FLTrust）差异具有统计显著性（$p<0.05$）。

**【英文翻译】**
The results demonstrate: FedAvg under mixed attacks suffers an ASR soaring to 92.34\%. While Krum manages to suppress the ASR to 12.15\%, it catastrophically inflates the FPR to 64.2\%, dragging accuracy down to 64.20\%. In stark contrast, the method proposed in this paper achieves the zenith of accuracy at 92.31\% while preserving an FPR of 0\%, simultaneously recording the lowest ASR (10.21\%). A Student's $t$-test based on multiple independent runs confirms that the variance, when juxtaposed against strong baselines (e.g., FLTrust), harbors statistical significance ($p<0.05$).

**【中文原文】**
\subsection{组件级核心机制消融分析 (Component-level Ablation Study)}
针对现有联邦安全研究中常出现的“黑盒式”效能评估，本节摒弃了粗粒度的阶段级叠加测试，转而采用组件级剥离实验，深入探究框架中双流正交解耦、多维风险探针与分层动态归一化等核心模块对防御鲁棒性与系统可用性的独立贡献。

\subsubsection{双流信誉解耦有效性分析}
为了验证系统极低的误杀率（FPR）并非来源于保守的防御阈值，而是得益于历史效用与瞬发风险的正交解耦设计，我们构建了两种退化变体进行对比：单流指数移动平均（Single-Stream EMA）与仅历史效用模型（HistPerf-Only）。表~\ref{tab:ablation_stream} 呈现了不同机制在强 Non-IID 及 30\% 混合攻击压力下的精确查杀表现。

**【英文翻译】**
\subsection{组件级核心机制消融分析 (Component-level Ablation Study)}
Addressing the ubiquitous "black-box" performance evaluations in current federated security research, this section abandons coarse-grained, phase-level superimposition tests in favor of component-level ablation experiments. This methodology rigorously investigates the independent contributions of core modules—such as dual-stream orthogonal decoupling, multi-dimensional risk probes, and layer-wise dynamic re-normalization—to defensive robustness and system availability.

\subsubsection{双流信誉解耦有效性分析}
To substantiate that the system's exceptionally low false positive rate (FPR) stems not from conservative defensive thresholds, but intrinsically from the orthogonal decoupling of historical utility and instantaneous risk, two degraded variants are constructed for comparison: a Single-Stream Exponential Moving Average (Single-Stream EMA) and a HistPerf-Only model. Table~\ref{tab:ablation_stream} delineates the precise interception performance of these divergent mechanisms under the intense pressure of severe Non-IID conditions and a 30\% mixed attack scenario.

**【中文原文】**
\begin{table}[htbp]
    \centering
    \caption{正交解耦对误杀率与召回率的作用剥离分析}
    \label{tab:ablation_stream}
    \begin{tabular}{l c c c}
        \toprule
        \textbf{信誉演化架构}                & \textbf{检测阈值控制} & \textbf{假阳率 (FPR)} & \textbf{真阳率 (TPR)} \\
        \midrule
        \multirow{2}{*}{单流 EMA (Baseline)} & 激进 (防投毒)         & 18.25\%               & 95.12\%               \\
                                             & 保守 (防误杀)         & 2.10\%                & 48.33\%               \\
        \midrule
        仅历史效用 (HistPerf-Only)           & 动态自适应            & 0.15\%                & 21.05\%               \\
        \textbf{双流正交解耦 (Ours)}         & 动态自适应            & \textbf{0.05\%}       & \textbf{98.50\%}      \\
        \bottomrule
    \end{tabular}
\end{table}

实验数据显示，单流机制在处理异构数据引起的偏离与恶意投毒时存在不可调和的矛盾：收紧阈值会导致高达 18.25\% 的无辜长尾节点被误杀；而放宽阈值则使 TPR 骤降，无法有效捕捉潜伏攻击。单独依赖历史效用流虽然能极好地包容长尾特征（FPR 为 0.15\%），但由于缺乏对短时突变的敏锐捕捉，其对“潜伏-爆发”式攻击的拦截率仅有 21.05\%。相较之下，本文提出的双流机制将长时贡献积累与短时风险熔断隔离处理，使得模型在无差别拦截 98.50\% 恶意节点的同时，精准保全了长尾诚实节点。

**【英文翻译】**
\begin{table}[htbp]
    \centering
    \caption{正交解耦对误杀率与召回率的作用剥离分析}
    \label{tab:ablation_stream}
    \begin{tabular}{l c c c}
        \toprule
        \textbf{信誉演化架构}                & \textbf{检测阈值控制} & \textbf{假阳率 (FPR)} & \textbf{真阳率 (TPR)} \\
        \midrule
        \multirow{2}{*}{单流 EMA (Baseline)} & 激进 (防投毒)         & 18.25\%               & 95.12\%               \\
                                             & 保守 (防误杀)         & 2.10\%                & 48.33\%               \\
        \midrule
        仅历史效用 (HistPerf-Only)           & 动态自适应            & 0.15\%                & 21.05\%               \\
        \textbf{双流正交解耦 (Ours)}         & 动态自适应            & \textbf{0.05\%}       & \textbf{98.50\%}      \\
        \bottomrule
    \end{tabular}
\end{table}

Experimental data reveals an irreconcilable paradox within the single-stream mechanism when mitigating deviations induced by data heterogeneity versus malicious poisoning: tightening the threshold precipitates a staggering 18.25\% misclassification of innocent long-tail nodes; conversely, relaxing the threshold plunges the TPR, rendering the system impotent against sleeper attacks. Relying exclusively on the historical utility stream adeptly accommodates long-tail features (yielding a diminutive FPR of 0.15\%); however, lacking acute sensitivity to short-term anomalies, its interception rate against "sleeper-burst" attacks barely reaches 21.05\%. In stark contrast, the dual-stream mechanism posited in this study segregates the accumulation of long-term contributions from short-term risk circuit breaking. Consequently, the model indiscriminately intercepts 98.50\% of malicious nodes while flawlessly safeguarding the integrity of honest long-tail nodes.

**【中文原文】**
\subsubsection{多维风险探针剥离分析}
在验证防御渗透效果时，单纯依赖纯净参考集往往无法全面应对多维度的复合攻击。图~\ref{fig:ablation_probes} 对比了仅启用纯净参考（Vanilla Clean-Root）、叠加浅层统计探针（+ Shallow Probes）以及全维深层探针（+ Full Probes）在面对无目标翻转、梯度缩放与隐蔽语义后门攻击时的 ASR 抑制效果。

\begin{figure}[htbp]
    \centering
    \includegraphics[width=0.75\textwidth]{fig9_ablation_probes.pdf}
    \caption{多维风险探针对不同渗透类型的攻击成功率（ASR）压制对比}
    \label{fig:ablation_probes}
\end{figure}

图表直观揭示了不同组件的防御壁垒：面对方向特征明显的无目标攻击，基准纯净参考结合浅层 L2 探针已能展现一定的压制力（ASR 约 11\%）；然而，当遭遇“干净标签投毒（Clean-Label Backdoor）”时，由于其梯度更新与正常方向高度共线，浅层机制几近失效，导致 ASR 飙升至 42.1\%。唯有当系统激活了基于交叉熵（$r_{probe}$）与高层特征 KL 散度（$r_{trigger}$）的深层探针后，才能敏锐捕捉到隐蔽后门触发器的微弱特征变异，将该类极强隐蔽性攻击的成功率强制压缩至 9.2\% 以下。

**【英文翻译】**
\subsubsection{多维风险探针剥离分析}
When verifying the efficacy against defensive penetration, a solitary reliance on a clean reference set frequently falls short of comprehensively neutralizing multi-dimensional compound attacks. Figure~\ref{fig:ablation_probes} contrasts the ASR suppression capabilities of merely employing a pristine reference (Vanilla Clean-Root), superimposing shallow statistical probes (+ Shallow Probes), and deploying full-dimensional deep probes (+ Full Probes) when confronted with untargeted flipping, gradient scaling, and stealthy semantic backdoor attacks.

\begin{figure}[htbp]
    \centering
    \includegraphics[width=0.75\textwidth]{fig9_ablation_probes.pdf}
    \caption{多维风险探针对不同渗透类型的攻击成功率（ASR）压制对比}
    \label{fig:ablation_probes}
\end{figure}

The visualization unequivocally unveils the defensive barriers erected by distinct components. Confronted with untargeted attacks exhibiting blatant directional features, the baseline clean reference coupled with shallow L2 probes exerts tangible suppression (restricting ASR to approximately 11\%). Nevertheless, upon encountering a "Clean-Label Backdoor," the shallow mechanism virtually collapses because its gradient updates remain highly collinear with the normal direction, causing the ASR to skyrocket to 42.1\%. Only when the system activates deep probes—predicated on cross-entropy ($r_{probe}$) and the KL divergence of high-level features ($r_{trigger}$)—can it astutely capture the subtle feature mutations of concealed backdoor triggers, forcibly compressing the success rate of such highly deceptive attacks to beneath 9.2\%.

**【中文原文】**
\subsubsection{分层门控与重归一化收敛效益}
在完成攻击剥离后，如何保障全局模型快速恢复可用性是另一核心议题。图~\ref{fig:ablation_renorm} 评估了传统全局一刀切裁剪（Global-Clipping）、仅执行分层门控但忽略权重重分配（Hierarchical w/o Renorm）与本文完整机制（Trust-Flow Ours）在收敛速率及最终精度上的差异。

\begin{figure}[htbp]
    \centering
    \includegraphics[width=0.75\textwidth]{fig10_ablation_renorm.pdf}
    \caption{动态权重重归一化机制对全局模型收敛速率及精度的增益效益}
    \label{fig:ablation_renorm}
\end{figure}

折线趋势清晰表明，粗暴的全局 L2 裁剪由于过度干预浅层特征提取层的权重更新，严重削弱了模型的泛化能力，导致最终精度停滞在 85\% 左右。尽管引入分层门控能在一定程度上缓解该问题（提升至 89\%），但在剔除恶意节点后，由于当轮有效聚合权重未达到单位约束（即 $\sum \tilde{w} < 1$），引发了“隐性学习率衰减”，使得收敛曲线依然滞后。本文引入的约束投影与权重重归一化机制，通过动态补偿幸存者的话语权，不仅在 80 轮左右实现了高速拟合，更将模型的理论上界推升至无攻击环境下的原生状态（92.4\%），从而在保障极高安全性的同时，实现了系统可用性的完全保全。

**【英文翻译】**
\subsubsection{分层门控与重归一化收敛效益}
Subsequent to the successful ablation of attacks, securing the rapid restoration of the global model's availability emerges as another pivotal concern. Figure~\ref{fig:ablation_renorm} evaluates the disparities in convergence velocity and terminal accuracy among a traditional, indiscriminate global clipping mechanism (Global-Clipping), the execution of layer-wise gating bereft of weight reallocation (Hierarchical w/o Renorm), and the holistic framework introduced herein (Trust-Flow Ours).

\begin{figure}[htbp]
    \centering
    \includegraphics[width=0.75\textwidth]{fig10_ablation_renorm.pdf}
    \caption{动态权重重归一化机制对全局模型收敛速率及精度的增益效益}
    \label{fig:ablation_renorm}
\end{figure}

The trajectory trends starkly indicate that the aggressive global L2 clipping profoundly dilutes the model's generalization capabilities by excessively interfering with the weight updates of the shallow feature extraction layers, effectively stalling the ultimate accuracy at approximately 85\%. Although incorporating layer-wise gating ameliorates this deficiency to an extent (elevating accuracy to 89\%), the elimination of malicious nodes precipitates a scenario where the effective aggregation weights of the current round fall short of the unit constraint (i.e., $\sum \tilde{w} < 1$). This instigates an "implicit learning rate decay," thereby ensuring the convergence curve remains retarded. The constrained projection and weight re-normalization mechanisms introduced in this study dynamically compensate for the influence of surviving nodes. This strategy not only orchestrates a high-speed fitting by round 80 but also propels the theoretical upper bound of the model back to its pristine state observed in attack-free environments (92.4\%), fully preserving system utility while maintaining uncompromising security.

**【中文原文】**
\subsection{长尾异构数据分布极限压力测试 (Sensitivity on Data Heterogeneity)}
许多鲁棒聚合方法对 IID 条件依赖较强。为评估本文框架在不同异构强度下的稳定性，本文在四组 Dirichlet 分布（$\alpha=100,1.0,\dots,0.1$）下测试全局准确率，结果见图~\ref{fig:alpha_sensitivity}。

\begin{figure}[htbp]
    \centering
    \includegraphics[width=0.85\textwidth]{fig11_alpha_sensitivity.pdf}
    \caption{环境数据异构度（Dirichlet $\alpha$）衰减下的各类安全聚合算法鲁棒性压力测试对比}
    \label{fig:alpha_sensitivity}
\end{figure}

从曲线可见：在 $\alpha=100$ 或 $\alpha=1.0$ 的弱异构场景下，Krum 与 FLTrust 表现接近本文方法（Acc 均大于 90\%）；但在极端长尾场景（$\alpha \to 0.1$）中，传统距离型方法明显退化，准确率最低降至 64.2\%。本文方法在同条件下仍稳定在约 92\%，说明双流解耦机制对强异构具有更好的鲁棒性。

此外，本文对关键参数 $\beta_{fusion}$ 做了离散测试（$[0.5,1.0,2.0,3.0]$）。较小取值有利于保留长尾节点，但 ASR 风险上升；过大取值会过度偏向同质更新。综合 Acc 与 ASR，最终选择 $\beta_{fusion}=2.0$。

**【英文翻译】**
\subsection{长尾异构数据分布极限压力测试 (Sensitivity on Data Heterogeneity)}
A plethora of robust aggregation methods lean heavily upon IID conditions. To meticulously evaluate the stability of the proposed framework under varying intensities of heterogeneity, the global accuracy was subjected to testing across four paradigms of Dirichlet distributions ($\alpha=100,1.0,\dots,0.1$), with the outcomes depicted in Figure~\ref{fig:alpha_sensitivity}.

\begin{figure}[htbp]
    \centering
    \includegraphics[width=0.85\textwidth]{fig11_alpha_sensitivity.pdf}
    \caption{环境数据异构度（Dirichlet $\alpha$）衰减下的各类安全聚合算法鲁棒性压力测试对比}
    \label{fig:alpha_sensitivity}
\end{figure}

The curves substantiate that within weakly heterogeneous environments dictated by $\alpha=100$ or $\alpha=1.0$, Krum and FLTrust exhibit performance rivaling the proposed method (both registering Acc $> 90\%$). However, within extreme long-tail settings ($\alpha \to 0.1$), traditional distance-based methods undergo marked degradation, with accuracy plummeting to a dismal 64.2\%. Resiliently, the proposed approach stabilizes at approximately 92\% under identical adversity, thereby verifying that the dual-stream decoupling architecture possesses superior robustness against profound heterogeneity.

Furthermore, discrete testing ($[0.5,1.0,2.0,3.0]$) was conducted on the pivotal parameter $\beta_{fusion}$. A smaller magnitude fosters the retention of long-tail nodes but simultaneously escalates ASR risks; conversely, an oversized value skews the aggregation excessively towards homogeneous updates. Weighing the trade-offs between Acc and ASR, $\beta_{fusion}=2.0$ was definitively selected.

**【中文原文】**
\subsection{系统计算与通信额外开销分析 (Overhead Analysis)}
尽管框架包含多阶段评估流程，其计算与通信开销仍可控。表~\ref{tab:overhead} 显示：边缘侧仅新增 TEE Quote 生成与轻量监测，额外延迟约 $12 \sim 15$ ms；通信侧每次仅附带约 $15$ KB 的 TrustReport，相对约 $10$ MB 量级模型传输，带宽增量低于 0.15\%。

\begin{table}[htbp]
    \centering
    \caption{传统联邦系统与本文可信联邦框架的端云开销对比 (20 Client)}
    \vspace{4pt}
    \label{tab:overhead}
    \begin{tabular}{l c c c}
        \toprule
        \textbf{系统架构}        & \textbf{边缘端额外计算延迟}         & \textbf{上行单次通信外加包大小}  & \textbf{云端中央聚合总耗时}             \\
        \midrule
        标准基线 FedAvg          & 0 ms (Baseline)                     & 0 KB (Baseline)                  & $\sim 2.10$ s                           \\
        \textbf{可信联邦 (Ours)} & \textbf{$\sim 15$ ms (仅 TEE 签名)} & \textbf{$\sim 15$ KB (附加报告)} & \textbf{$\sim 4.85$ s (包含审查与双流)} \\
        \bottomrule
    \end{tabular}
\end{table}

代价方面，分层余弦评估会增加服务器端计算量。测试中单轮聚合耗时由 $2.10$ s 增至 $4.85$ s。考虑到广域网场景单轮通信通常在数十秒量级，该开销在工程上可接受。

**【英文翻译】**
\subsection{系统计算与通信额外开销分析 (Overhead Analysis)}
Despite harboring a multi-phase evaluation protocol, the computational and communication overhead of the framework remains stringently tractable. Table~\ref{tab:overhead} demonstrates that the edge merely incurs the generation of a TEE Quote and lightweight monitoring, yielding an auxiliary delay of roughly $12 \sim 15$ ms. Concurrently, the communication tier merely appends a TrustReport of approximately $15$ KB per transmission. When juxtaposed against the $\sim 10$ MB scale of model transfer, the bandwidth overhead rests below an imperceptible 0.15\%.

\begin{table}[htbp]
    \centering
    \caption{传统联邦系统与本文可信联邦框架的端云开销对比 (20 Client)}
    \vspace{4pt}
    \label{tab:overhead}
    \begin{tabular}{l c c c}
        \toprule
        \textbf{系统架构}        & \textbf{边缘端额外计算延迟}         & \textbf{上行单次通信外加包大小}  & \textbf{云端中央聚合总耗时}             \\
        \midrule
        标准基线 FedAvg          & 0 ms (Baseline)                     & 0 KB (Baseline)                  & $\sim 2.10$ s                           \\
        \textbf{可信联邦 (Ours)} & \textbf{$\sim 15$ ms (仅 TEE 签名)} & \textbf{$\sim 15$ KB (附加报告)} & \textbf{$\sim 4.85$ s (包含审查与双流)} \\
        \bottomrule
    \end{tabular}
\end{table}

Regarding specific costs, the layer-wise cosine evaluation inherently inflates the computational load on the server. In our empirical trials, the aggregation duration per round escalated from $2.10$ s to $4.85$ s. Given that a single round of communication over a Wide Area Network (WAN) habitually consumes tens of seconds, this nominal computational overhead is entirely acceptable from an engineering perspective.

**【中文原文】**
\section{结论与未来展望}
本文面向边缘联邦学习在强 Non-IID 与混合攻击下的安全问题，提出了“硬件可信准入 + 双流信誉演化 + 分层鲁棒聚合”的 Trust-Flow TFL 框架。该框架通过 TEE 提供物理信任根，并在算法层以 HistPerf 和 RiskEMA 的正交建模实现“低误杀与高召回”的协同。

实验结果表明，框架在 30\% 混合攻击下取得 $92.31\% (\pm 0.09\%)$ 的准确率与 $10.21\% (\pm 0.05\%)$ 的 ASR；在 50\% 边界压力测试下仍保持稳定性能，并实现 TPR=100\%、FPR=0\%（永久封禁口径）。这说明该方法在强对抗和强异构条件下具有较好的实用性。

\textbf{局限性与后续工作}：由于部分 TEE-FL 新方法尚未公开可复现实现，本文未将其纳入同构对比基线，后续计划随论文定稿开放代码与实验脚本，便于社区复现和扩展。未来还将把风险探针从 CV 场景扩展到 LLM/NLP 联邦微调任务，以验证跨模态场景下的泛化能力。

**【英文翻译】**
\section{结论与未来展望}
Addressing the security vulnerabilities of edge federated learning amidst potent Non-IID constraints and compound attacks, this manuscript formally introduces the Trust-Flow TFL framework, a triad architecture encompassing "hardware-anchored trusted admission, dual-stream reputation evolution, and layer-wise robust aggregation." This framework instantiates a physical root of trust via TEEs and mathematically engineers the synergy of "low false positives paired with high recall" at the algorithmic tier through the orthogonal modeling of $HistPerf$ and $RiskEMA$.

Empirical results dictate that under a 30\% mixed attack vector, the framework attains an accuracy of $92.31\% (\pm 0.09\%)$ and restricts ASR to $10.21\% (\pm 0.05\%)$. Even subjected to the 50\% boundary pressure test, it perseveres with steadfast stability, delivering a perfect TPR of 100\% alongside an FPR of 0\% (metricized by permanent bans). This rigorously confirms the method's robust utility under profoundly adversarial and intensely heterogeneous paradigms.

\textbf{Limitations and Future Trajectories}: Due to the absence of publicly verifiable implementations for several emerging TEE-FL methodologies, this study foregoes their inclusion within the isomorphic comparative baselines. Subsequent phases aim to release the source code and experimental scripts alongside the final manuscript publication, thereby catalyzing community reproduction and expansion. Future endeavors will also endeavor to scale these multidimensional risk probes beyond CV environments into LLM/NLP federated fine-tuning topologies, meticulously validating their generalizability across cross-modal scenarios.

**【中文原文】**
\appendix
\section{瞬发风险流 (Risk Flow) 探针计算机制细节}
为增强可复现性与透明度，本附录给出第 4 节瞬时风险流核心探针（$r_{grad}, r_{probe}, r_{trigger}$）的计算细节。第 $t$ 轮聚合时各探针定义如下：

\subsection{A.1 梯度方向与幅度物理探针 ($r_{grad}$)}
$r_{grad}$ 衡量客户端更新 $\Delta W_k^{(t)}$ 与参考方向 $g_{root}^{(t)}$ 的几何偏离，用于检测符号翻转与幅度异常。该指标同时考虑方向偏离（余弦项）与尺度突变（L2 异常项）：
\begin{equation}
    r_{grad, k}^{(t)} = \lambda_{d} \left(1 - \frac{\Delta W_k^{(t)} \cdot g_{root}^{(t)}}{||\Delta W_k^{(t)}|| \cdot ||g_{root}^{(t)}||}\right) + \lambda_{m} \max\left(0, \frac{||\Delta W_k^{(t)}||_2 - \mu^{(t)}}{\sigma^{(t)}}\right)
\end{equation}
其中，$\lambda_d$ 与 $\lambda_m$ 控制方向项和幅度项的权重（默认均为 $0.5$）；$\mu^{(t)}$ 与 $\sigma^{(t)}$ 分别为第 $t$ 轮入围节点梯度 L2 范数的均值与标准差。

\subsection{A.2 小样本先验验证交叉熵探针 ($r_{probe}$)}
仅靠距离统计难以识别对非主类的定向污染。$r_{probe}$ 使用服务器侧小规模纯净探针集 $\mathcal{D}_{probe}$，比较合并前后交叉熵损失增量（Loss Surge）：
\begin{equation}
    r_{probe, k}^{(t)} = \text{ReLU}\left( \mathcal{L}_{CE}(W_{global}^{(t-1)} + \Delta W_k^{(t)}; \mathcal{D}_{probe}) - \mathcal{L}_{CE}(W_{global}^{(t-1)}; \mathcal{D}_{probe}) \right)
\end{equation}

\subsection{A.3 深层神经元隐蔽后门激活探针 ($r_{trigger}$)}
针对 Clean-Label 等高隐蔽攻击，常规统计与验证 Loss 可能不足。$r_{trigger}$ 通过高层特征激活分布差异进行检测。设 $A_k$ 为客户端模型在验证集上的前置激活输出，$\mathcal{H}(\cdot)$ 表示 Softmax 归一化到概率单形，以满足 KL 散度计算条件：
\begin{equation}
    r_{trigger, k}^{(t)} = \text{KL-Divergence}\left( \mathcal{H}(A_{base}) \| \mathcal{H}(A_k) \right)
\end{equation}

上述三类异常信号经归一化融合后形成单轮风险值 $Risk_{k}^{(t)}$，并进入 EMA 更新，用于后续快速熔断决策。

**【英文翻译】**
\appendix
\section{瞬发风险流 (Risk Flow) 探针计算机制细节}
To augment reproducibility and transparency, this appendix mathematically delineates the calculation details of the core probes ($r_{grad}, r_{probe}, r_{trigger}$) underpinning the instant risk stream originally introduced in Section 4. During the $t$-th aggregation round, the probes are defined as follows:

\subsection{A.1 梯度方向与幅度物理探针 ($r_{grad}$)}
The $r_{grad}$ probe quantifies the geometric deviation of the client update $\Delta W_k^{(t)}$ relative to the reference direction $g_{root}^{(t)}$, tasked specifically with detecting sign flipping and amplitude anomalies. This metric concurrently evaluates directional deflection (cosine term) and scale mutation (L2 anomaly term):
\begin{equation}
    r_{grad, k}^{(t)} = \lambda_{d} \left(1 - \frac{\Delta W_k^{(t)} \cdot g_{root}^{(t)}}{||\Delta W_k^{(t)}|| \cdot ||g_{root}^{(t)}||}\right) + \lambda_{m} \max\left(0, \frac{||\Delta W_k^{(t)}||_2 - \mu^{(t)}}{\sigma^{(t)}}\right)
\end{equation}
Wherein $\lambda_d$ and $\lambda_m$ modulate the weighting of the directional and amplitude terms, respectively (defaulting to $0.5$ for both); $\mu^{(t)}$ and $\sigma^{(t)}$ signify the mean and standard deviation of the gradient L2 norms across the admitted nodes for round $t$.

\subsection{A.2 小样本先验验证交叉熵探针 ($r_{probe}$)}
Relying exclusively on distance statistics is grossly inadequate for identifying targeted pollution directed against minority classes. The $r_{probe}$ leverages a small-scale, pristine probe set on the server, denoted as $\mathcal{D}_{probe}$, calculating the incremental surge in cross-entropy loss (Loss Surge) pre- and post-merger:
\begin{equation}
    r_{probe, k}^{(t)} = \text{ReLU}\left( \mathcal{L}_{CE}(W_{global}^{(t-1)} + \Delta W_k^{(t)}; \mathcal{D}_{probe}) - \mathcal{L}_{CE}(W_{global}^{(t-1)}; \mathcal{D}_{probe}) \right)
\end{equation}

\subsection{A.3 深层神经元隐蔽后门激活探针 ($r_{trigger}$)}
Countering profoundly concealed threats like Clean-Label attacks, standard statistical and validation losses often fall short. The $r_{trigger}$ discerns anomalies through the distributional variance of high-level feature activations. Assuming $A_k$ denotes the client model's pre-activation outputs on the validation set, and $\mathcal{H}(\cdot)$ signifies the Softmax normalization into a probability simplex to satisfy the KL-Divergence prerequisites:
\begin{equation}
    r_{trigger, k}^{(t)} = \text{KL-Divergence}\left( \mathcal{H}(A_{base}) \| \mathcal{H}(A_k) \right)
\end{equation}

Post normalization and fusion, these three distinct anomalous signals crystallize into the single-round risk extremum $Risk_{k}^{(t)}$, rapidly entering the EMA pipeline to empower subsequent fast-circuit breaking adjudication.

**【中文原文】**
\begin{thebibliography}{99}
    \bibitem{kairouz2021flsurvey} Kairouz P, McMahan H B, Avent B, et al. Advances and Open Problems in Federated Learning[J]. Foundations and Trends in Machine Learning, 2021.
    \bibitem{gu2017badnets} Gu T, Dolan-Gavitt B, Garg S. BadNets: Identifying Vulnerabilities in the Machine Learning Model Supply Chain[J]. arXiv:1708.06733, 2017.
    \bibitem{wang2019neuralcleanse} Wang B, Yao Y, Shan S, et al. Neural Cleanse: Identifying and Mitigating Backdoor Attacks in Neural Networks[C]. IEEE S\&P, 2019.
    \bibitem{blanchard2017krum} Blanchard P, El Mhamdi E M, Guerraoui R, et al. Machine Learning with Adversaries: Byzantine Tolerant Gradient Descent[C]. NeurIPS, 2017.
    \bibitem{yin2018byzantine} Yin D, Chen Y, Kannan R, et al. Byzantine-Robust Distributed Learning: Towards Optimal Statistical Rates[C]. ICML, 2018.
    \bibitem{pillutla2022robust} Pillutla K, Kakade S M, Harchaoui Z. Robust Aggregation for Federated Learning[J]. IEEE Transactions on Signal Processing, 2022.
    \bibitem{cao2021fltrust} Cao X, Fang M, Liu J, et al. FLTrust: Byzantine-Robust Federated Learning via Trust Bootstrapping[J]. NDSS, 2021.
    \bibitem{fung2020foolsgold} Fung C, Yoon C J M, Beschastnikh I. The Limitations of Federated Learning in Sybil Settings[C]. RAID, 2020.
    \bibitem{r9_clustered} Towards Privacy-Enhanced and Robust Clustered Federated Learning[J].
    \bibitem{fedpe} FedPE: Adaptive Model Pruning-Expanding for Federated Learning on Mobile Devices[J].
    \bibitem{parallelsfl} ParallelSFL: A Novel Split Federated Learning Framework Tackling Heterogeneity Issues[J].
    \bibitem{wang2025rasa} Wang et al. RaSA: Robust and Adaptive Secure Aggregation for Edge-Assisted Hierarchical Federated Learning[J]. 2025.
    \bibitem{dou2025toward} Dou et al. Toward Malicious Clients Detection in Federated Learning[J]. 2025.
    \bibitem{lu2025tmt} Lu et al. TMT-FL: Enabling Trustworthy Model Training of Federated Learning With Malicious Participants[J]. 2025.
    \bibitem{wang2024federated} Wang et al. A Federated Learning Scheme with Adaptive Hierarchical Protection and Multiple Aggregation[J]. 2024.
    \bibitem{flpurifier} FLPurifier: Backdoor Defense in Federated Learning via Decoupled Contrastive Training[J].
    \bibitem{roseagg} RoseAgg: Robust Defense Against Targeted Collusion Attacks in Federated Learning[J].
    \bibitem{shieldfl} ShieldFL: Mitigating Model Poisoning Attacks in Privacy-Preserving Federated Learning[J].
    \bibitem{liao2024verifiable} Liao et al. Verifiable Deep Learning Inference on Heterogeneous Edge Devices With Trusted Execution Environment[J]. 2024.
    \bibitem{zhang2025rppfl} Zhang et al. RPPFL: Robust and Privacy-Preserving Federated Learning via Trusted Execution Environments[J]. 2025.
    \bibitem{r1_tee_integrity} A training-integrity privacy-preserving federated learning scheme with trusted execution environment[J].
    \bibitem{r5_tee_mitigating} Queyrut S, Schiavoni V, Felber P. Mitigating Adversarial Attacks in Federated Learning with Trusted Execution Environments[C]. ICDCS, 2023.
    \bibitem{r12_iot_tee} Secure sharing of industrial IoT data based on distributed trust management and trusted execution environment[J].
    \bibitem{xu2021distributed} Xu et al. Distributed Learning in Trusted Execution Environment A Case Study of Federated Learning in SGX[J]. 2021.
    \bibitem{yan2024efficient} Yan et al. An Efficient Greedy Hierarchical Federated Learning Training Method Based on Trusted Execution Environment[J]. 2024.
    \bibitem{mcmahan2017fedavg} McMahan B, Moore E, Ramage D, et al. Communication-Efficient Learning of Deep Networks from Decentralized Data[J]. AISTATS, 2017.
    \bibitem{chen2017maximum} Chen B, Xing L, Zhao H, et al. Maximum correntropy Kalman filter[J]. Automatica, 2017, 76: 70-77.
    \bibitem{li2026multidimensional} Multidimensional Trust Evaluation and Task Match Based Workers Recruitment Scheme for MCS[J]. IEEE Transactions on Dependable and Secure Computing, 2026.
\end{thebibliography}
\end{document}

**【英文翻译】**
\begin{thebibliography}{99}
    \bibitem{kairouz2021flsurvey} Kairouz P, McMahan H B, Avent B, et al. Advances and Open Problems in Federated Learning[J]. Foundations and Trends in Machine Learning, 2021.
    \bibitem{gu2017badnets} Gu T, Dolan-Gavitt B, Garg S. BadNets: Identifying Vulnerabilities in the Machine Learning Model Supply Chain[J]. arXiv:1708.06733, 2017.
    \bibitem{wang2019neuralcleanse} Wang B, Yao Y, Shan S, et al. Neural Cleanse: Identifying and Mitigating Backdoor Attacks in Neural Networks[C]. IEEE S\&P, 2019.
    \bibitem{blanchard2017krum} Blanchard P, El Mhamdi E M, Guerraoui R, et al. Machine Learning with Adversaries: Byzantine Tolerant Gradient Descent[C]. NeurIPS, 2017.
    \bibitem{yin2018byzantine} Yin D, Chen Y, Kannan R, et al. Byzantine-Robust Distributed Learning: Towards Optimal Statistical Rates[C]. ICML, 2018.
    \bibitem{pillutla2022robust} Pillutla K, Kakade S M, Harchaoui Z. Robust Aggregation for Federated Learning[J]. IEEE Transactions on Signal Processing, 2022.
    \bibitem{cao2021fltrust} Cao X, Fang M, Liu J, et al. FLTrust: Byzantine-Robust Federated Learning via Trust Bootstrapping[J]. NDSS, 2021.
    \bibitem{fung2020foolsgold} Fung C, Yoon C J M, Beschastnikh I. The Limitations of Federated Learning in Sybil Settings[C]. RAID, 2020.
    \bibitem{r9_clustered} Towards Privacy-Enhanced and Robust Clustered Federated Learning[J].
    \bibitem{fedpe} FedPE: Adaptive Model Pruning-Expanding for Federated Learning on Mobile Devices[J].
    \bibitem{parallelsfl} ParallelSFL: A Novel Split Federated Learning Framework Tackling Heterogeneity Issues[J].
    \bibitem{wang2025rasa} Wang et al. RaSA: Robust and Adaptive Secure Aggregation for Edge-Assisted Hierarchical Federated Learning[J]. 2025.
    \bibitem{dou2025toward} Dou et al. Toward Malicious Clients Detection in Federated Learning[J]. 2025.
    \bibitem{lu2025tmt} Lu et al. TMT-FL: Enabling Trustworthy Model Training of Federated Learning With Malicious Participants[J]. 2025.
    \bibitem{wang2024federated} Wang et al. A Federated Learning Scheme with Adaptive Hierarchical Protection and Multiple Aggregation[J]. 2024.
    \bibitem{flpurifier} FLPurifier: Backdoor Defense in Federated Learning via Decoupled Contrastive Training[J].
    \bibitem{roseagg} RoseAgg: Robust Defense Against Targeted Collusion Attacks in Federated Learning[J].
    \bibitem{shieldfl} ShieldFL: Mitigating Model Poisoning Attacks in Privacy-Preserving Federated Learning[J].
    \bibitem{liao2024verifiable} Liao et al. Verifiable Deep Learning Inference on Heterogeneous Edge Devices With Trusted Execution Environment[J]. 2024.
    \bibitem{zhang2025rppfl} Zhang et al. RPPFL: Robust and Privacy-Preserving Federated Learning via Trusted Execution Environments[J]. 2025.
    \bibitem{r1_tee_integrity} A training-integrity privacy-preserving federated learning scheme with trusted execution environment[J].
    \bibitem{r5_tee_mitigating} Queyrut S, Schiavoni V, Felber P. Mitigating Adversarial Attacks in Federated Learning with Trusted Execution Environments[C]. ICDCS, 2023.
    \bibitem{r12_iot_tee} Secure sharing of industrial IoT data based on distributed trust management and trusted execution environment[J].
    \bibitem{xu2021distributed} Xu et al. Distributed Learning in Trusted Execution Environment A Case Study of Federated Learning in SGX[J]. 2021.
    \bibitem{yan2024efficient} Yan et al. An Efficient Greedy Hierarchical Federated Learning Training Method Based on Trusted Execution Environment[J]. 2024.
    \bibitem{mcmahan2017fedavg} McMahan B, Moore E, Ramage D, et al. Communication-Efficient Learning of Deep Networks from Decentralized Data[J]. AISTATS, 2017.
    \bibitem{chen2017maximum} Chen B, Xing L, Zhao H, et al. Maximum correntropy Kalman filter[J]. Automatica, 2017, 76: 70-77.
    \bibitem{li2026multidimensional} Multidimensional Trust Evaluation and Task Match Based Workers Recruitment Scheme for MCS[J]. IEEE Transactions on Dependable and Secure Computing, 2026.
\end{thebibliography}
\end{document}

**【中文原文】**
\subsection{组件级核心机制消融分析 (Component-level Ablation Study)}
针对现有联邦安全研究中常出现的“黑盒式”效能评估，本节摒弃了粗粒度的阶段级叠加测试，转而采用组件级剥离实验，深入探究框架中双流正交解耦、多维风险探针与分层动态归一化等核心模块对防御鲁棒性与系统可用性的独立贡献。

\subsubsection{双流信誉解耦有效性分析}
为了验证系统极低的误杀率（FPR）并非来源于保守的防御阈值，而是得益于历史效用与瞬发风险的正交解耦设计，我们构建了两种退化变体进行对比：单流指数移动平均（Single-Stream EMA）与仅历史效用模型（HistPerf-Only）。表~\ref{tab:ablation_stream} 呈现了不同机制在强 Non-IID 及 30\% 混合攻击压力下的精确查杀表现。

**【英文翻译】**
\subsection{组件级核心机制消融分析 (Component-level Ablation Study)}
Addressing the ubiquitous "black-box" performance evaluations in current federated security research, this section abandons coarse-grained, phase-level superimposition tests in favor of component-level ablation experiments. This methodology rigorously investigates the independent contributions of core modules—such as dual-stream orthogonal decoupling, multi-dimensional risk probes, and layer-wise dynamic re-normalization—to defensive robustness and system availability.

\subsubsection{双流信誉解耦有效性分析}
To substantiate that the system's exceptionally low false positive rate (FPR) stems not from conservative defensive thresholds, but intrinsically from the orthogonal decoupling of historical utility and instantaneous risk, two degraded variants are constructed for comparison: a Single-Stream Exponential Moving Average (Single-Stream EMA) and a HistPerf-Only model. Table~\ref{tab:ablation_stream} delineates the precise interception performance of these divergent mechanisms under the intense pressure of severe Non-IID conditions and a 30\% mixed attack scenario.

**【中文原文】**
\begin{table}[htbp]
    \centering
    \caption{正交解耦对误杀率与召回率的作用剥离分析}
    \label{tab:ablation_stream}
    \begin{tabular}{l c c c}
        \toprule
        \textbf{信誉演化架构}                & \textbf{检测阈值控制} & \textbf{假阳率 (FPR)} & \textbf{真阳率 (TPR)} \\
        \midrule
        \multirow{2}{*}{单流 EMA (Baseline)} & 激进 (防投毒)         & 18.25\%               & 95.12\%               \\
                                             & 保守 (防误杀)         & 2.10\%                & 48.33\%               \\
        \midrule
        仅历史效用 (HistPerf-Only)           & 动态自适应            & 0.15\%                & 21.05\%               \\
        \textbf{双流正交解耦 (Ours)}         & 动态自适应            & \textbf{0.05\%}       & \textbf{98.50\%}      \\
        \bottomrule
    \end{tabular}
\end{table}

实验数据显示，单流机制在处理异构数据引起的偏离与恶意投毒时存在不可调和的矛盾：收紧阈值会导致高达 18.25\% 的无辜长尾节点被误杀；而放宽阈值则使 TPR 骤降，无法有效捕捉潜伏攻击。单独依赖历史效用流虽然能极好地包容长尾特征（FPR 为 0.15\%），但由于缺乏对短时突变的敏锐捕捉，其对“潜伏-爆发”式攻击的拦截率仅有 21.05\%。相较之下，本文提出的双流机制将长时贡献积累与短时风险熔断隔离处理，使得模型在无差别拦截 98.50\% 恶意节点的同时，精准保全了长尾诚实节点。

**【英文翻译】**
\begin{table}[htbp]
    \centering
    \caption{正交解耦对误杀率与召回率的作用剥离分析}
    \label{tab:ablation_stream}
    \begin{tabular}{l c c c}
        \toprule
        \textbf{信誉演化架构}                & \textbf{检测阈值控制} & \textbf{假阳率 (FPR)} & \textbf{真阳率 (TPR)} \\
        \midrule
        \multirow{2}{*}{单流 EMA (Baseline)} & 激进 (防投毒)         & 18.25\%               & 95.12\%               \\
                                             & 保守 (防误杀)         & 2.10\%                & 48.33\%               \\
        \midrule
        仅历史效用 (HistPerf-Only)           & 动态自适应            & 0.15\%                & 21.05\%               \\
        \textbf{双流正交解耦 (Ours)}         & 动态自适应            & \textbf{0.05\%}       & \textbf{98.50\%}      \\
        \bottomrule
    \end{tabular}
\end{table}

Experimental data reveals an irreconcilable paradox within the single-stream mechanism when mitigating deviations induced by data heterogeneity versus malicious poisoning: tightening the threshold precipitates a staggering 18.25\% misclassification of innocent long-tail nodes; conversely, relaxing the threshold plunges the TPR, rendering the system impotent against sleeper attacks. Relying exclusively on the historical utility stream adeptly accommodates long-tail features (yielding a diminutive FPR of 0.15\%); however, lacking acute sensitivity to short-term anomalies, its interception rate against "sleeper-burst" attacks barely reaches 21.05\%. In stark contrast, the dual-stream mechanism posited in this study segregates the accumulation of long-term contributions from short-term risk circuit breaking. Consequently, the model indiscriminately intercepts 98.50\% of malicious nodes while flawlessly safeguarding the integrity of honest long-tail nodes.

**【中文原文】**
\subsubsection{多维风险探针剥离分析}
在验证防御渗透效果时，单纯依赖纯净参考集往往无法全面应对多维度的复合攻击。图~\ref{fig:ablation_probes} 对比了仅启用纯净参考（Vanilla Clean-Root）、叠加浅层统计探针（+ Shallow Probes）以及全维深层探针（+ Full Probes）在面对无目标翻转、梯度缩放与隐蔽语义后门攻击时的 ASR 抑制效果。

\begin{figure}[htbp]
    \centering
    \includegraphics[width=0.75\textwidth]{fig9_ablation_probes.pdf}
    \caption{多维风险探针对不同渗透类型的攻击成功率（ASR）压制对比}
    \label{fig:ablation_probes}
\end{figure}

图表直观揭示了不同组件的防御壁垒：面对方向特征明显的无目标攻击，基准纯净参考结合浅层 L2 探针已能展现一定的压制力（ASR 约 11\%）；然而，当遭遇“干净标签投毒（Clean-Label Backdoor）”时，由于其梯度更新与正常方向高度共线，浅层机制几近失效，导致 ASR 飙升至 42.1\%。唯有当系统激活了基于交叉熵（$r_{probe}$）与高层特征 KL 散度（$r_{trigger}$）的深层探针后，才能敏锐捕捉到隐蔽后门触发器的微弱特征变异，将该类极强隐蔽性攻击的成功率强制压缩至 9.2\% 以下。

**【英文翻译】**
\subsubsection{多维风险探针剥离分析}
When verifying the efficacy against defensive penetration, a solitary reliance on a clean reference set frequently falls short of comprehensively neutralizing multi-dimensional compound attacks. Figure~\ref{fig:ablation_probes} contrasts the ASR suppression capabilities of merely employing a pristine reference (Vanilla Clean-Root), superimposing shallow statistical probes (+ Shallow Probes), and deploying full-dimensional deep probes (+ Full Probes) when confronted with untargeted flipping, gradient scaling, and stealthy semantic backdoor attacks.

\begin{figure}[htbp]
    \centering
    \includegraphics[width=0.75\textwidth]{fig9_ablation_probes.pdf}
    \caption{多维风险探针对不同渗透类型的攻击成功率（ASR）压制对比}
    \label{fig:ablation_probes}
\end{figure}

The visualization unequivocally unveils the defensive barriers erected by distinct components. Confronted with untargeted attacks exhibiting blatant directional features, the baseline clean reference coupled with shallow L2 probes exerts tangible suppression (restricting ASR to approximately 11\%). Nevertheless, upon encountering a "Clean-Label Backdoor," the shallow mechanism virtually collapses because its gradient updates remain highly collinear with the normal direction, causing the ASR to skyrocket to 42.1\%. Only when the system activates deep probes—predicated on cross-entropy ($r_{probe}$) and the KL divergence of high-level features ($r_{trigger}$)—can it astutely capture the subtle feature mutations of concealed backdoor triggers, forcibly compressing the success rate of such highly deceptive attacks to beneath 9.2\%.

**【中文原文】**
\subsubsection{分层门控与重归一化收敛效益}
在完成攻击剥离后，如何保障全局模型快速恢复可用性是另一核心议题。图~\ref{fig:ablation_renorm} 评估了传统全局一刀切裁剪（Global-Clipping）、仅执行分层门控但忽略权重重分配（Hierarchical w/o Renorm）与本文完整机制（Trust-Flow Ours）在收敛速率及最终精度上的差异。

\begin{figure}[htbp]
    \centering
    \includegraphics[width=0.75\textwidth]{fig10_ablation_renorm.pdf}
    \caption{动态权重重归一化机制对全局模型收敛速率及精度的增益效益}
    \label{fig:ablation_renorm}
\end{figure}

折线趋势清晰表明，粗暴的全局 L2 裁剪由于过度干预浅层特征提取层的权重更新，严重削弱了模型的泛化能力，导致最终精度停滞在 85\% 左右。尽管引入分层门控能在一定程度上缓解该问题（提升至 89\%），但在剔除恶意节点后，由于当轮有效聚合权重未达到单位约束（即 $\sum \tilde{w} < 1$），引发了“隐性学习率衰减”，使得收敛曲线依然滞后。本文引入的约束投影与权重重归一化机制，通过动态补偿幸存者的话语权，不仅在 80 轮左右实现了高速拟合，更将模型的理论上界推升至无攻击环境下的原生状态（92.4\%），从而在保障极高安全性的同时，实现了系统可用性的完全保全。

**【英文翻译】**
\subsubsection{分层门控与重归一化收敛效益}
Subsequent to the successful ablation of attacks, securing the rapid restoration of the global model's availability emerges as another pivotal concern. Figure~\ref{fig:ablation_renorm} evaluates the disparities in convergence velocity and terminal accuracy among a traditional, indiscriminate global clipping mechanism (Global-Clipping), the execution of layer-wise gating bereft of weight reallocation (Hierarchical w/o Renorm), and the holistic framework introduced herein (Trust-Flow Ours).

\begin{figure}[htbp]
    \centering
    \includegraphics[width=0.75\textwidth]{fig10_ablation_renorm.pdf}
    \caption{动态权重重归一化机制对全局模型收敛速率及精度的增益效益}
    \label{fig:ablation_renorm}
\end{figure}

The trajectory trends starkly indicate that the aggressive global L2 clipping profoundly dilutes the model's generalization capabilities by excessively interfering with the weight updates of the shallow feature extraction layers, effectively stalling the ultimate accuracy at approximately 85\%. Although incorporating layer-wise gating ameliorates this deficiency to an extent (elevating accuracy to 89\%), the elimination of malicious nodes precipitates a scenario where the effective aggregation weights of the current round fall short of the unit constraint (i.e., $\sum \tilde{w} < 1$). This instigates an "implicit learning rate decay," thereby ensuring the convergence curve remains retarded. The constrained projection and weight re-normalization mechanisms introduced in this study dynamically compensate for the influence of surviving nodes. This strategy not only orchestrates a high-speed fitting by round 80 but also propels the theoretical upper bound of the model back to its pristine state observed in attack-free environments (92.4\%), fully preserving system utility while maintaining uncompromising security.

**【中文原文】**
\subsection{长尾异构数据分布极限压力测试 (Sensitivity on Data Heterogeneity)}
许多鲁棒聚合方法对 IID 条件依赖较强。为评估本文框架在不同异构强度下的稳定性，本文在四组 Dirichlet 分布（$\alpha=100,1.0,\dots,0.1$）下测试全局准确率，结果见图~\ref{fig:alpha_sensitivity}。

\begin{figure}[htbp]
    \centering
    \includegraphics[width=0.85\textwidth]{fig11_alpha_sensitivity.pdf}
    \caption{环境数据异构度（Dirichlet $\alpha$）衰减下的各类安全聚合算法鲁棒性压力测试对比}
    \label{fig:alpha_sensitivity}
\end{figure}

从曲线可见：在 $\alpha=100$ 或 $\alpha=1.0$ 的弱异构场景下，Krum 与 FLTrust 表现接近本文方法（Acc 均大于 90\%）；但在极端长尾场景（$\alpha \to 0.1$）中，传统距离型方法明显退化，准确率最低降至 64.2\%。本文方法在同条件下仍稳定在约 92\%，说明双流解耦机制对强异构具有更好的鲁棒性。

此外，本文对关键参数 $\beta_{fusion}$ 做了离散测试（$[0.5,1.0,2.0,3.0]$）。较小取值有利于保留长尾节点，但 ASR 风险上升；过大取值会过度偏向同质更新。综合 Acc 与 ASR，最终选择 $\beta_{fusion}=2.0$。

**【英文翻译】**
\subsection{长尾异构数据分布极限压力测试 (Sensitivity on Data Heterogeneity)}
A plethora of robust aggregation methods lean heavily upon IID conditions. To meticulously evaluate the stability of the proposed framework under varying intensities of heterogeneity, the global accuracy was subjected to testing across four paradigms of Dirichlet distributions ($\alpha=100,1.0,\dots,0.1$), with the outcomes depicted in Figure~\ref{fig:alpha_sensitivity}.

\begin{figure}[htbp]
    \centering
    \includegraphics[width=0.85\textwidth]{fig11_alpha_sensitivity.pdf}
    \caption{环境数据异构度（Dirichlet $\alpha$）衰减下的各类安全聚合算法鲁棒性压力测试对比}
    \label{fig:alpha_sensitivity}
\end{figure}

The curves substantiate that within weakly heterogeneous environments dictated by $\alpha=100$ or $\alpha=1.0$, Krum and FLTrust exhibit performance rivaling the proposed method (both registering Acc $> 90\%$). However, within extreme long-tail settings ($\alpha \to 0.1$), traditional distance-based methods undergo marked degradation, with accuracy plummeting to a dismal 64.2\%. Resiliently, the proposed approach stabilizes at approximately 92\% under identical adversity, thereby verifying that the dual-stream decoupling architecture possesses superior robustness against profound heterogeneity.

Furthermore, discrete testing ($[0.5,1.0,2.0,3.0]$) was conducted on the pivotal parameter $\beta_{fusion}$. A smaller magnitude fosters the retention of long-tail nodes but simultaneously escalates ASR risks; conversely, an oversized value skews the aggregation excessively towards homogeneous updates. Weighing the trade-offs between Acc and ASR, $\beta_{fusion}=2.0$ was definitively selected.

**【中文原文】**
\subsection{系统计算与通信额外开销分析 (Overhead Analysis)}
尽管框架包含多阶段评估流程，其计算与通信开销仍可控。表~\ref{tab:overhead} 显示：边缘侧仅新增 TEE Quote 生成与轻量监测，额外延迟约 $12 \sim 15$ ms；通信侧每次仅附带约 $15$ KB 的 TrustReport，相对约 $10$ MB 量级模型传输，带宽增量低于 0.15\%。

\begin{table}[htbp]
    \centering
    \caption{传统联邦系统与本文可信联邦框架的端云开销对比 (20 Client)}
    \vspace{4pt}
    \label{tab:overhead}
    \begin{tabular}{l c c c}
        \toprule
        \textbf{系统架构}        & \textbf{边缘端额外计算延迟}         & \textbf{上行单次通信外加包大小}  & \textbf{云端中央聚合总耗时}             \\
        \midrule
        标准基线 FedAvg          & 0 ms (Baseline)                     & 0 KB (Baseline)                  & $\sim 2.10$ s                           \\
        \textbf{可信联邦 (Ours)} & \textbf{$\sim 15$ ms (仅 TEE 签名)} & \textbf{$\sim 15$ KB (附加报告)} & \textbf{$\sim 4.85$ s (包含审查与双流)} \\
        \bottomrule
    \end{tabular}
\end{table}

代价方面，分层余弦评估会增加服务器端计算量。测试中单轮聚合耗时由 $2.10$ s 增至 $4.85$ s。考虑到广域网场景单轮通信通常在数十秒量级，该开销在工程上可接受。

**【英文翻译】**
\subsection{系统计算与通信额外开销分析 (Overhead Analysis)}
Despite harboring a multi-phase evaluation protocol, the computational and communication overhead of the framework remains stringently tractable. Table~\ref{tab:overhead} demonstrates that the edge merely incurs the generation of a TEE Quote and lightweight monitoring, yielding an auxiliary delay of roughly $12 \sim 15$ ms. Concurrently, the communication tier merely appends a TrustReport of approximately $15$ KB per transmission. When juxtaposed against the $\sim 10$ MB scale of model transfer, the bandwidth overhead rests below an imperceptible 0.15\%.

\begin{table}[htbp]
    \centering
    \caption{传统联邦系统与本文可信联邦框架的端云开销对比 (20 Client)}
    \vspace{4pt}
    \label{tab:overhead}
    \begin{tabular}{l c c c}
        \toprule
        \textbf{系统架构}        & \textbf{边缘端额外计算延迟}         & \textbf{上行单次通信外加包大小}  & \textbf{云端中央聚合总耗时}             \\
        \midrule
        标准基线 FedAvg          & 0 ms (Baseline)                     & 0 KB (Baseline)                  & $\sim 2.10$ s                           \\
        \textbf{可信联邦 (Ours)} & \textbf{$\sim 15$ ms (仅 TEE 签名)} & \textbf{$\sim 15$ KB (附加报告)} & \textbf{$\sim 4.85$ s (包含审查与双流)} \\
        \bottomrule
    \end{tabular}
\end{table}

Regarding specific costs, the layer-wise cosine evaluation inherently inflates the computational load on the server. In our empirical trials, the aggregation duration per round escalated from $2.10$ s to $4.85$ s. Given that a single round of communication over a Wide Area Network (WAN) habitually consumes tens of seconds, this nominal computational overhead is entirely acceptable from an engineering perspective.

**【中文原文】**
\section{结论与未来展望}
本文面向边缘联邦学习在强 Non-IID 与混合攻击下的安全问题，提出了“硬件可信准入 + 双流信誉演化 + 分层鲁棒聚合”的 Trust-Flow TFL 框架。该框架通过 TEE 提供物理信任根，并在算法层以 HistPerf 和 RiskEMA 的正交建模实现“低误杀与高召回”的协同。

实验结果表明，框架在 30\% 混合攻击下取得 $92.31\% (\pm 0.09\%)$ 的准确率与 $10.21\% (\pm 0.05\%)$ 的 ASR；在 50\% 边界压力测试下仍保持稳定性能，并实现 TPR=100\%、FPR=0\%（永久封禁口径）。这说明该方法在强对抗和强异构条件下具有较好的实用性。

\textbf{局限性与后续工作}：由于部分 TEE-FL 新方法尚未公开可复现实现，本文未将其纳入同构对比基线，后续计划随论文定稿开放代码与实验脚本，便于社区复现和扩展。未来还将把风险探针从 CV 场景扩展到 LLM/NLP 联邦微调任务，以验证跨模态场景下的泛化能力。

**【英文翻译】**
\section{结论与未来展望}
Addressing the security vulnerabilities of edge federated learning amidst potent Non-IID constraints and compound attacks, this manuscript formally introduces the Trust-Flow TFL framework, a triad architecture encompassing "hardware-anchored trusted admission, dual-stream reputation evolution, and layer-wise robust aggregation." This framework instantiates a physical root of trust via TEEs and mathematically engineers the synergy of "low false positives paired with high recall" at the algorithmic tier through the orthogonal modeling of $HistPerf$ and $RiskEMA$.

Empirical results dictate that under a 30\% mixed attack vector, the framework attains an accuracy of $92.31\% (\pm 0.09\%)$ and restricts ASR to $10.21\% (\pm 0.05\%)$. Even subjected to the 50\% boundary pressure test, it perseveres with steadfast stability, delivering a perfect TPR of 100\% alongside an FPR of 0\% (metricized by permanent bans). This rigorously confirms the method's robust utility under profoundly adversarial and intensely heterogeneous paradigms.

\textbf{Limitations and Future Trajectories}: Due to the absence of publicly verifiable implementations for several emerging TEE-FL methodologies, this study foregoes their inclusion within the isomorphic comparative baselines. Subsequent phases aim to release the source code and experimental scripts alongside the final manuscript publication, thereby catalyzing community reproduction and expansion. Future endeavors will also endeavor to scale these multidimensional risk probes beyond CV environments into LLM/NLP federated fine-tuning topologies, meticulously validating their generalizability across cross-modal scenarios.

**【中文原文】**
\appendix
\section{瞬发风险流 (Risk Flow) 探针计算机制细节}
为增强可复现性与透明度，本附录给出第 4 节瞬时风险流核心探针（$r_{grad}, r_{probe}, r_{trigger}$）的计算细节。第 $t$ 轮聚合时各探针定义如下：

\subsection{A.1 梯度方向与幅度物理探针 ($r_{grad}$)}
$r_{grad}$ 衡量客户端更新 $\Delta W_k^{(t)}$ 与参考方向 $g_{root}^{(t)}$ 的几何偏离，用于检测符号翻转与幅度异常。该指标同时考虑方向偏离（余弦项）与尺度突变（L2 异常项）：
\begin{equation}
    r_{grad, k}^{(t)} = \lambda_{d} \left(1 - \frac{\Delta W_k^{(t)} \cdot g_{root}^{(t)}}{||\Delta W_k^{(t)}|| \cdot ||g_{root}^{(t)}||}\right) + \lambda_{m} \max\left(0, \frac{||\Delta W_k^{(t)}||_2 - \mu^{(t)}}{\sigma^{(t)}}\right)
\end{equation}
其中，$\lambda_d$ 与 $\lambda_m$ 控制方向项和幅度项的权重（默认均为 $0.5$）；$\mu^{(t)}$ 与 $\sigma^{(t)}$ 分别为第 $t$ 轮入围节点梯度 L2 范数的均值与标准差。

\subsection{A.2 小样本先验验证交叉熵探针 ($r_{probe}$)}
仅靠距离统计难以识别对非主类的定向污染。$r_{probe}$ 使用服务器侧小规模纯净探针集 $\mathcal{D}_{probe}$，比较合并前后交叉熵损失增量（Loss Surge）：
\begin{equation}
    r_{probe, k}^{(t)} = \text{ReLU}\left( \mathcal{L}_{CE}(W_{global}^{(t-1)} + \Delta W_k^{(t)}; \mathcal{D}_{probe}) - \mathcal{L}_{CE}(W_{global}^{(t-1)}; \mathcal{D}_{probe}) \right)
\end{equation}

\subsection{A.3 深层神经元隐蔽后门激活探针 ($r_{trigger}$)}
针对 Clean-Label 等高隐蔽攻击，常规统计与验证 Loss 可能不足。$r_{trigger}$ 通过高层特征激活分布差异进行检测。设 $A_k$ 为客户端模型在验证集上的前置激活输出，$\mathcal{H}(\cdot)$ 表示 Softmax 归一化到概率单形，以满足 KL 散度计算条件：
\begin{equation}
    r_{trigger, k}^{(t)} = \text{KL-Divergence}\left( \mathcal{H}(A_{base}) \| \mathcal{H}(A_k) \right)
\end{equation}

上述三类异常信号经归一化融合后形成单轮风险值 $Risk_{k}^{(t)}$，并进入 EMA 更新，用于后续快速熔断决策。

**【英文翻译】**
\appendix
\section{瞬发风险流 (Risk Flow) 探针计算机制细节}
To augment reproducibility and transparency, this appendix mathematically delineates the calculation details of the core probes ($r_{grad}, r_{probe}, r_{trigger}$) underpinning the instant risk stream originally introduced in Section 4. During the $t$-th aggregation round, the probes are defined as follows:

\subsection{A.1 梯度方向与幅度物理探针 ($r_{grad}$)}
The $r_{grad}$ probe quantifies the geometric deviation of the client update $\Delta W_k^{(t)}$ relative to the reference direction $g_{root}^{(t)}$, tasked specifically with detecting sign flipping and amplitude anomalies. This metric concurrently evaluates directional deflection (cosine term) and scale mutation (L2 anomaly term):
\begin{equation}
    r_{grad, k}^{(t)} = \lambda_{d} \left(1 - \frac{\Delta W_k^{(t)} \cdot g_{root}^{(t)}}{||\Delta W_k^{(t)}|| \cdot ||g_{root}^{(t)}||}\right) + \lambda_{m} \max\left(0, \frac{||\Delta W_k^{(t)}||_2 - \mu^{(t)}}{\sigma^{(t)}}\right)
\end{equation}
Wherein $\lambda_d$ and $\lambda_m$ modulate the weighting of the directional and amplitude terms, respectively (defaulting to $0.5$ for both); $\mu^{(t)}$ and $\sigma^{(t)}$ signify the mean and standard deviation of the gradient L2 norms across the admitted nodes for round $t$.

\subsection{A.2 小样本先验验证交叉熵探针 ($r_{probe}$)}
Relying exclusively on distance statistics is grossly inadequate for identifying targeted pollution directed against minority classes. The $r_{probe}$ leverages a small-scale, pristine probe set on the server, denoted as $\mathcal{D}_{probe}$, calculating the incremental surge in cross-entropy loss (Loss Surge) pre- and post-merger:
\begin{equation}
    r_{probe, k}^{(t)} = \text{ReLU}\left( \mathcal{L}_{CE}(W_{global}^{(t-1)} + \Delta W_k^{(t)}; \mathcal{D}_{probe}) - \mathcal{L}_{CE}(W_{global}^{(t-1)}; \mathcal{D}_{probe}) \right)
\end{equation}

\subsection{A.3 深层神经元隐蔽后门激活探针 ($r_{trigger}$)}
Countering profoundly concealed threats like Clean-Label attacks, standard statistical and validation losses often fall short. The $r_{trigger}$ discerns anomalies through the distributional variance of high-level feature activations. Assuming $A_k$ denotes the client model's pre-activation outputs on the validation set, and $\mathcal{H}(\cdot)$ signifies the Softmax normalization into a probability simplex to satisfy the KL-Divergence prerequisites:
\begin{equation}
    r_{trigger, k}^{(t)} = \text{KL-Divergence}\left( \mathcal{H}(A_{base}) \| \mathcal{H}(A_k) \right)
\end{equation}

Post normalization and fusion, these three distinct anomalous signals crystallize into the single-round risk extremum $Risk_{k}^{(t)}$, rapidly entering the EMA pipeline to empower subsequent fast-circuit breaking adjudication.

**【中文原文】**
\begin{thebibliography}{99}
    \bibitem{kairouz2021flsurvey} Kairouz P, McMahan H B, Avent B, et al. Advances and Open Problems in Federated Learning[J]. Foundations and Trends in Machine Learning, 2021.
    \bibitem{gu2017badnets} Gu T, Dolan-Gavitt B, Garg S. BadNets: Identifying Vulnerabilities in the Machine Learning Model Supply Chain[J]. arXiv:1708.06733, 2017.
    \bibitem{wang2019neuralcleanse} Wang B, Yao Y, Shan S, et al. Neural Cleanse: Identifying and Mitigating Backdoor Attacks in Neural Networks[C]. IEEE S\&P, 2019.
    \bibitem{blanchard2017krum} Blanchard P, El Mhamdi E M, Guerraoui R, et al. Machine Learning with Adversaries: Byzantine Tolerant Gradient Descent[C]. NeurIPS, 2017.
    \bibitem{yin2018byzantine} Yin D, Chen Y, Kannan R, et al. Byzantine-Robust Distributed Learning: Towards Optimal Statistical Rates[C]. ICML, 2018.
    \bibitem{pillutla2022robust} Pillutla K, Kakade S M, Harchaoui Z. Robust Aggregation for Federated Learning[J]. IEEE Transactions on Signal Processing, 2022.
    \bibitem{cao2021fltrust} Cao X, Fang M, Liu J, et al. FLTrust: Byzantine-Robust Federated Learning via Trust Bootstrapping[J]. NDSS, 2021.
    \bibitem{fung2020foolsgold} Fung C, Yoon C J M, Beschastnikh I. The Limitations of Federated Learning in Sybil Settings[C]. RAID, 2020.
    \bibitem{r9_clustered} Towards Privacy-Enhanced and Robust Clustered Federated Learning[J].
    \bibitem{fedpe} FedPE: Adaptive Model Pruning-Expanding for Federated Learning on Mobile Devices[J].
    \bibitem{parallelsfl} ParallelSFL: A Novel Split Federated Learning Framework Tackling Heterogeneity Issues[J].
    \bibitem{wang2025rasa} Wang et al. RaSA: Robust and Adaptive Secure Aggregation for Edge-Assisted Hierarchical Federated Learning[J]. 2025.
    \bibitem{dou2025toward} Dou et al. Toward Malicious Clients Detection in Federated Learning[J]. 2025.
    \bibitem{lu2025tmt} Lu et al. TMT-FL: Enabling Trustworthy Model Training of Federated Learning With Malicious Participants[J]. 2025.
    \bibitem{wang2024federated} Wang et al. A Federated Learning Scheme with Adaptive Hierarchical Protection and Multiple Aggregation[J]. 2024.
    \bibitem{flpurifier} FLPurifier: Backdoor Defense in Federated Learning via Decoupled Contrastive Training[J].
    \bibitem{roseagg} RoseAgg: Robust Defense Against Targeted Collusion Attacks in Federated Learning[J].
    \bibitem{shieldfl} ShieldFL: Mitigating Model Poisoning Attacks in Privacy-Preserving Federated Learning[J].
    \bibitem{liao2024verifiable} Liao et al. Verifiable Deep Learning Inference on Heterogeneous Edge Devices With Trusted Execution Environment[J]. 2024.
    \bibitem{zhang2025rppfl} Zhang et al. RPPFL: Robust and Privacy-Preserving Federated Learning via Trusted Execution Environments[J]. 2025.
    \bibitem{r1_tee_integrity} A training-integrity privacy-preserving federated learning scheme with trusted execution environment[J].
    \bibitem{r5_tee_mitigating} Queyrut S, Schiavoni V, Felber P. Mitigating Adversarial Attacks in Federated Learning with Trusted Execution Environments[C]. ICDCS, 2023.
    \bibitem{r12_iot_tee} Secure sharing of industrial IoT data based on distributed trust management and trusted execution environment[J].
    \bibitem{xu2021distributed} Xu et al. Distributed Learning in Trusted Execution Environment A Case Study of Federated Learning in SGX[J]. 2021.
    \bibitem{yan2024efficient} Yan et al. An Efficient Greedy Hierarchical Federated Learning Training Method Based on Trusted Execution Environment[J]. 2024.
    \bibitem{mcmahan2017fedavg} McMahan B, Moore E, Ramage D, et al. Communication-Efficient Learning of Deep Networks from Decentralized Data[J]. AISTATS, 2017.
    \bibitem{chen2017maximum} Chen B, Xing L, Zhao H, et al. Maximum correntropy Kalman filter[J]. Automatica, 2017, 76: 70-77.
    \bibitem{li2026multidimensional} Multidimensional Trust Evaluation and Task Match Based Workers Recruitment Scheme for MCS[J]. IEEE Transactions on Dependable and Secure Computing, 2026.
\end{thebibliography}
\end{document}

**【英文翻译】**
\begin{thebibliography}{99}
    \bibitem{kairouz2021flsurvey} Kairouz P, McMahan H B, Avent B, et al. Advances and Open Problems in Federated Learning[J]. Foundations and Trends in Machine Learning, 2021.
    \bibitem{gu2017badnets} Gu T, Dolan-Gavitt B, Garg S. BadNets: Identifying Vulnerabilities in the Machine Learning Model Supply Chain[J]. arXiv:1708.06733, 2017.
    \bibitem{wang2019neuralcleanse} Wang B, Yao Y, Shan S, et al. Neural Cleanse: Identifying and Mitigating Backdoor Attacks in Neural Networks[C]. IEEE S\&P, 2019.
    \bibitem{blanchard2017krum} Blanchard P, El Mhamdi E M, Guerraoui R, et al. Machine Learning with Adversaries: Byzantine Tolerant Gradient Descent[C]. NeurIPS, 2017.
    \bibitem{yin2018byzantine} Yin D, Chen Y, Kannan R, et al. Byzantine-Robust Distributed Learning: Towards Optimal Statistical Rates[C]. ICML, 2018.
    \bibitem{pillutla2022robust} Pillutla K, Kakade S M, Harchaoui Z. Robust Aggregation for Federated Learning[J]. IEEE Transactions on Signal Processing, 2022.
    \bibitem{cao2021fltrust} Cao X, Fang M, Liu J, et al. FLTrust: Byzantine-Robust Federated Learning via Trust Bootstrapping[J]. NDSS, 2021.
    \bibitem{fung2020foolsgold} Fung C, Yoon C J M, Beschastnikh I. The Limitations of Federated Learning in Sybil Settings[C]. RAID, 2020.
    \bibitem{r9_clustered} Towards Privacy-Enhanced and Robust Clustered Federated Learning[J].
    \bibitem{fedpe} FedPE: Adaptive Model Pruning-Expanding for Federated Learning on Mobile Devices[J].
    \bibitem{parallelsfl} ParallelSFL: A Novel Split Federated Learning Framework Tackling Heterogeneity Issues[J].
    \bibitem{wang2025rasa} Wang et al. RaSA: Robust and Adaptive Secure Aggregation for Edge-Assisted Hierarchical Federated Learning[J]. 2025.
    \bibitem{dou2025toward} Dou et al. Toward Malicious Clients Detection in Federated Learning[J]. 2025.
    \bibitem{lu2025tmt} Lu et al. TMT-FL: Enabling Trustworthy Model Training of Federated Learning With Malicious Participants[J]. 2025.
    \bibitem{wang2024federated} Wang et al. A Federated Learning Scheme with Adaptive Hierarchical Protection and Multiple Aggregation[J]. 2024.
    \bibitem{flpurifier} FLPurifier: Backdoor Defense in Federated Learning via Decoupled Contrastive Training[J].
    \bibitem{roseagg} RoseAgg: Robust Defense Against Targeted Collusion Attacks in Federated Learning[J].
    \bibitem{shieldfl} ShieldFL: Mitigating Model Poisoning Attacks in Privacy-Preserving Federated Learning[J].
    \bibitem{liao2024verifiable} Liao et al. Verifiable Deep Learning Inference on Heterogeneous Edge Devices With Trusted Execution Environment[J]. 2024.
    \bibitem{zhang2025rppfl} Zhang et al. RPPFL: Robust and Privacy-Preserving Federated Learning via Trusted Execution Environments[J]. 2025.
    \bibitem{r1_tee_integrity} A training-integrity privacy-preserving federated learning scheme with trusted execution environment[J].
    \bibitem{r5_tee_mitigating} Queyrut S, Schiavoni V, Felber P. Mitigating Adversarial Attacks in Federated Learning with Trusted Execution Environments[C]. ICDCS, 2023.
    \bibitem{r12_iot_tee} Secure sharing of industrial IoT data based on distributed trust management and trusted execution environment[J].
    \bibitem{xu2021distributed} Xu et al. Distributed Learning in Trusted Execution Environment A Case Study of Federated Learning in SGX[J]. 2021.
    \bibitem{yan2024efficient} Yan et al. An Efficient Greedy Hierarchical Federated Learning Training Method Based on Trusted Execution Environment[J]. 2024.
    \bibitem{mcmahan2017fedavg} McMahan B, Moore E, Ramage D, et al. Communication-Efficient Learning of Deep Networks from Decentralized Data[J]. AISTATS, 2017.
    \bibitem{chen2017maximum} Chen B, Xing L, Zhao H, et al. Maximum correntropy Kalman filter[J]. Automatica, 2017, 76: 70-77.
    \bibitem{li2026multidimensional} Multidimensional Trust Evaluation and Task Match Based Workers Recruitment Scheme for MCS[J]. IEEE Transactions on Dependable and Secure Computing, 2026.
\end{thebibliography}
\end{document}
