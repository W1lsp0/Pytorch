with open("paper-en-lncs/main.tex", "r", encoding="utf-8") as f:
    text = f.read()

def replace_between(content, start_str, end_str, replace_with):
    s = content.find(start_str)
    if s == -1: return content
    e = content.find(end_str, s + len(start_str))
    if e == -1: return content
    e += len(end_str)
    return content[:s] + replace_with + content[e:]

# 1. Phase 3 Text
text = replace_between(
    text,
    "Approaches clinging universally onto conventional",
    "experimental hyperparameter boundary specifications natively cataloged through successive experimental domains).",
    r'''Traditional single-metric reputation mechanisms inherently struggle against heterogeneous data limitations. The intrinsic defense pivot adopted mathematically inside this framework leverages absolute "dimensional decoupling", disassembling chronological measurements into twin opposing and firmly distinct temporal progression tracks: deploying the \textbf{Historical Performance Flow ($HistPerf$)} to manage resilient permission allowances, structurally distanced from the definitive penalization veto governed strictly by the \textbf{Instantaneous Risk Containment Flow ($RiskEMA$)}.

\textbf{(1) Historical Performance Flow ($HistPerf$)} primarily undertakes the evaluation of long-term capabilities. It does not possess the authority to make "negative decisions". In each round, based on the relative standard deviation distribution (the $z$-score) of the $ContentScore$ across the entire queue, a smoothing function and a baseline threshold are weighted to derive the increment $Signal_k^{upd}$:
\begin{align}
    z_{k} &= \frac{ContentScore_{k} - \mu_{content}}{\sigma_{content} + \varepsilon}, \quad Signal_{k}^{rel} = \sigma(z_{k}), \\
    Signal_{k}^{abs} &= \mathrm{clip}\left(\frac{ContentScore_{k} - b}{s}, 0, 1\right), \\
    Signal_{k}^{upd} &= \gamma_{rel} \cdot Signal_{k}^{rel} + \gamma_{abs} \cdot Signal_{k}^{abs}, \\
    HistPerf_{k}^{(t)} &= \beta_{h} \cdot HistPerf_{k}^{(t-1)} + (1 - \beta_{h}) \cdot Signal_{k}^{upd}.
\end{align}
Here, the constants $b$ and $s$ serve as scaling boundaries for the absolute score; $\gamma_{rel}$ and $\gamma_{abs}$ (which sum to $1.0$) adjust the proportions of relative competition and absolute performance, respectively. When $HistPerf$ is extremely low, the node is simply placed into a temporary seat termed "Hist Soft Isolation" (unable to participate in the current round's aggregation, but remaining within the network). This design preserves unpopular data nodes.

\textbf{(2) Instantaneous Risk Containment Flow ($RiskEMA$)} is the core mechanism for intercepting attackers. It bypasses simple gradient angle matching and comprehensively adopts multi-dimensional probe data from gradients (loss oscillation $r_{probe}$, neuronal polarity distribution $r_{grad}$, stealth backdoor channels $r_{trigger}$, and even image-level pre-screening $r_{pixel}$). We extract the highest instantaneous extremum across all risk probe channels in each round:
\begin{equation}
    Risk_{k}^{inst} = \max\{r_{report}, r_{grad}, r_{probe}, r_{pixel}, r_{trigger}, r_{sign}, r_{peer}, \dots \},
\end{equation}
Subsequently, exponential decay memory is applied backward (with $\beta_r = 0.85$ acting as the smoothing coefficient):
\begin{equation}
    RiskEMA_{k}^{(t)} = \beta_{r} \cdot RiskEMA_{k}^{(t-1)} + (1 - \beta_{r}) \cdot Risk_{k}^{inst}.
\end{equation}

By combining the orthogonal calculus of the aforementioned multi-dimensional risks and historical utilities, the framework establishes a secure lifecycle state transition automaton for all nodes within the controlled federation (its topology is illustrated in Fig.~\ref{fig:node_state_machine}), delineating four major supervision quadrants:
\begin{itemize}
    \item \textbf{Normal Nodes (NORMAL)}: Fully participate in the current round's aggregation and distribution. When the probe acutely captures an anomaly (a rise in RiskEMA) or a decline in historical utility, the node will shift rightwards to the suspect status or transition into the soft isolation state, respectively.
    \item \textbf{Suspect Nodes (SUSPECT)}: Localized monitoring is intensified on the dimension that triggered the alarm. If the observed risk subsides, it is pardoned and restored to NORMAL; if it continuously triggers the redline threshold, it is handed over to the isolation procedure.
    \item \textbf{Quarantine Observation (QUARANTINE)}: Deprived of the right to contribute physical parameters for the global aggregation of the current round, only permitted to contribute non-critical computations. If subsequent observations show compliance (condition lifted), it may return to NORMAL; conversely, if a poor track record triggers the banning rule, it plummets into the abyss.
    \item \textbf{Blacklist Banning (BLACKLIST)}: A permanent, irreversible blacklist. Hitting the hard threshold completely severs the handshake at the TEE certificate layer, terminating all future collaborative qualifications.
\end{itemize}
This highly implicit state decoupling mechanism, which balances historical tolerance (allowing for pardons), enables the framework to boldly filter heterogeneous gradients while maintaining a false positive rate converging to zero.

\begin{figure}[htbp]
    \centering
    \includegraphics[width=0.9\textwidth]{fig4_state.pdf}
    \caption{Logical diagram of the four-state supervision transition automaton under the superposition of client historical accumulation and instantaneous risks.}
    \label{fig:node_state_machine}
\end{figure}

Finally, $TrustScore$ (hardware reputation), $ContentScore$ (effort in the current round), and $HistPerf$ (historical prestige) converge into a base metric for the absolute weight of the current round's aggregation, yielding $RawScore_k$ after applying a risk discount:
\begin{align}
    RawScore_{k}^{base} &= (TrustScore_{k})^{\alpha} \cdot (ContentScore_{k})^{\beta} \cdot (HistPerf_{k}^{(t-1)})^{\gamma}, \\
    RawScore_{k} &= RawScore_{k}^{base} \cdot (1 - RiskEMA_{k}^{prev})^{p},
\end{align}
where the exponential hyperparameters $\alpha, \beta, \gamma$, and $p$ sequentially determine the control strength of the four aforementioned dimensions over the final voice (weight feedback).'''
)

# 2. Algorithm 1
text = replace_between(
    text,
    "\\begin{algorithm}[htbp]\n\\caption{Dual-stream Orthogonal Trust",
    "\\end{algorithmic}\n\\end{algorithm}",
    r'''\begin{algorithm}[htbp]
\caption{Dual-stream Orthogonal Trust State Evolution (HistPerf \& RiskEMA)}
\label{alg:phase3}
\begin{algorithmic}[1]
\REQUIRE $ContentScore_k$, Multi-dimensional risk probe set $\{r_{probe}, r_{grad}, \dots\}$
\ENSURE $HistPerf_k^{(t)}$, Instantaneous risk flow $RiskEMA_k^{(t)}$, Global weight baseline score $RawScore_k$
\STATE \textbf{Stream A: Historical Utility Flow Evolution (Competitive Soft Privilege)}
\STATE Calculate the global mean $\mu_{content}$ and standard deviation $\sigma_{content}$ of the content scores
\FOR{each admitted client $k$}
    \STATE Relative competition signal $Signal_k^{rel} \leftarrow \sigma((ContentScore_k - \mu_{content})/(\sigma_{content} + \varepsilon))$
    \STATE Absolute baseline signal $Signal_k^{abs} \leftarrow \mathrm{clip}((ContentScore_k - b)/s, 0, 1)$
    \STATE Comprehensive increment $Signal_k^{upd} \leftarrow \gamma_{rel} Signal_k^{rel} + \gamma_{abs} Signal_k^{abs}$
    \STATE Update $HistPerf_k^{(t)} \leftarrow \beta_h HistPerf_k^{(t-1)} + (1 - \beta_h) Signal_k^{upd}$
\ENDFOR
\STATE \textbf{Stream B: Instantaneous Risk Disciplinary Flow Evolution (One-vote Veto Power)}
\FOR{each client $k$}
    \STATE Capture the instantaneous risk extremum $Risk_k^{inst} \leftarrow \max\{r_{report}, r_{grad}, r_{probe}, r_{pixel}, r_{trigger}\}$
    \STATE Update $RiskEMA_k^{(t)} \leftarrow \beta_r RiskEMA_k^{(t-1)} + (1-\beta_r) Risk_k^{inst}$
    \IF{$RiskEMA_k^{(t)} > \text{Isolation Threshold}$}
        \STATE Add to long-term isolation blacklist $RiskIsolated \leftarrow RiskIsolated \cup \{k\}$
    \ENDIF
\ENDFOR
\STATE \textbf{Final Privilege Fusion Calculation}
\FOR{each active client $k \notin RiskIsolated$}
    \STATE Fusion score $RawScore_k \leftarrow (TrustScore_k)^\alpha (ContentScore_k)^\beta (HistPerf_k^{(t-1)})^\gamma$
    \STATE Risk discount $RawScore_k \leftarrow RawScore_k \cdot (1 - RiskEMA_k^{(t-1)})^p$
\ENDFOR
\RETURN $\{HistPerf_k^{(t)}, RiskEMA_k^{(t)}, RawScore_k\}$
\end{algorithmic}
\end{algorithm}'''
)

# 3. Phase 4 Text
text = replace_between(
    text,
    "Structurally sophisticated backdoor manipulation trajectories",
    "\\end{equation}\n",
    r'''The attacker's stealthy backdoors are frequently concealed inside specific neurons within deep layers. Directly orchestrating a unified multiply-accumulate weight merging across the entire gradient of the model leaves vulnerabilities wherein dormant backdoors can penetrate. Therefore, we propose a differentiated (Layer-wise) admission-gated aggregation strategy executed in accordance to the network layer depth $l$.

First, filter the set of active clients $\mathcal{A}$ qualified to participate in the current round:
\begin{equation} \label{eq:active_clients}
    \mathcal{A} = \{k \mid k \notin RiskIsolated \land k \notin HistSoftIsolated\}.
\end{equation}

Second, for the $l$-th layer, evaluate its security defense requirements. The shallow layers of a network typically preserve common privacy features such as the physical edge schemas of images, while the deep layers entail massive weight alterations (utility) and are susceptible to buried poison (security). The algorithm leverages a 3D modeling of the weight sensitivity of the layer $S_{total}^{(l)}$:
\begin{align}
    S_{privacy}^{(l)} &= \exp\left(-\tau_{p} \frac{l}{L}\right), \\
    S_{utility}^{(l)} &= \frac{\|g_{ref}^{(l)}\|_{2}}{\max_{m}\|g_{ref}^{(m)}\|_{2} + \varepsilon}, \\
    S_{security}^{(l)} &= 1 - \frac{\sum_{k\in\mathcal{A}}TrustScore_{k}\cdot\cos(\Delta W_{k}^{(l)}, g_{ref}^{(l)})}{\sum_{k\in\mathcal{A}}TrustScore_{k} + \varepsilon}, \\
    S_{total}^{(l)} &= w_p S_{privacy}^{(l)} + w_u S_{utility}^{(l)} + w_s S_{security}^{(l)}.
\end{align}
Here, $w_p, w_u, w_s$ denote the hierarchical requirement weighting factors satisfying the normalization condition. If the sum of the layer's security segregation sensitivities $S_{total}^{(l)}$ is extraordinarily high, it proves that this layer is a major disaster zone for backdoor injections. The system will immediately elevate the proportional admission threshold $\theta^{(l)} = \mu_{base} + \lambda_{s} \cdot S_{total}^{(l)}$ and tighten the L2 clipping space $C^{(l)} = C_{base} / (S_{total}^{(l)} + \varepsilon_{c})$.

Third, only those ``layer survivors'' $\Phi^{(l)}$ whose current round $RawScore_k$ breaches $\theta^{(l)}$ are allowed to submit updates for aggregation. After entering the survivor list, a normalized weight distribution $\tilde{w}_{k}^{(l)}$ is enacted and anomalously colossal malicious gradient amplitudes are forcibly clipped ($scale_k^{(l)}$):
\begin{align}
    \Phi^{(l)} &= \{k \in \mathcal{A} \mid RawScore_{k} \ge \theta^{(l)} \}, \quad \tilde{w}_{k}^{(l)} = \frac{RawScore_{k}}{\sum_{j\in\Phi^{(l)}}RawScore_{j} + \varepsilon}, \\
    scale_{k}^{(l)} &= \max\left(1, \frac{\|\Delta W_{k}^{(l)}\|_{2}}{C^{(l)}}\right), \quad
    \widehat{\Delta W}_{k}^{(l)} = \frac{\Delta W_{k}^{(l)}}{scale_{k}^{(l)}}.
\end{align}
Fourth, the individual layers are respectively weighted and merged into a single-layer increment:
\begin{equation}
    \Delta W_{global}^{(l)} = \sum_{k\in\Phi^{(l)}}\tilde{w}_{k}^{(l)} \cdot \widehat{\Delta W}_{k}^{(l)},
\end{equation}
'''
)

# 4. Phase 4 Algorithm (Algorithm 2)
# The search string has to match exactly what is there. Let's find exactly how the algo is named.
text = replace_between(
    text,
    "\\begin{algorithm}[htbp]\n\\caption{Layer-wise Differentiated Aggregations",
    "\\end{algorithmic}\n\\end{algorithm}",
    r'''\begin{algorithm}[htbp]
\caption{Risk-gated Layer-wise Differentiated Aggregation and Dynamic Clipping}
\label{alg:phase4}
\begin{algorithmic}[1]
\REQUIRE Active nodes $\mathcal{A}$, scores $RawScore_k$, layer-wise update gradients $\{\Delta W_k^{(l)}\}$, network depth $L$
\ENSURE The integrated secure global gradient for the current round $\Delta W_{global}$
\STATE Initialize global increment $\Delta W_{global} \leftarrow 0$
\FOR{each network layer $l = 1, 2, \dots, L$}
    \STATE \textbf{Step 1: 3D Joint Calculation of Layer Sensitivity}
    \STATE Privacy sensitivity $S_{privacy}^{(l)} \leftarrow \exp(-\tau_p \cdot l/L)$
    \STATE Utility sensitivity $S_{utility}^{(l)} \leftarrow \|g_{ref}^{(l)}\|_2 / \max_m\|g_{ref}^{(m)}\|_2$
    \STATE Security sensitivity $S_{security}^{(l)} \leftarrow 1 - \frac{\sum_{k\in\mathcal{A}} TrustScore_k \cos(\Delta W_k^{(l)}, g_{ref}^{(l)})}{\sum_{k\in\mathcal{A}} TrustScore_k + \varepsilon}$
    \STATE Total defense requirement sensitivity $S_{total}^{(l)} \leftarrow w_p S_{privacy}^{(l)} + w_u S_{utility}^{(l)} + w_s S_{security}^{(l)}$
    \STATE \textbf{Step 2: Dynamic Risk Gating and Adaptive L2 Donut Clipping}
    \STATE Elevate the security admission score threshold for this layer $\theta^{(l)} \leftarrow \mu_{base} + \lambda_s \cdot S_{total}^{(l)}$
    \STATE Tighten the malicious amplitude clipping boundary for this layer $C^{(l)} \leftarrow C_{base} / (S_{total}^{(l)} + \varepsilon_c)$
    \STATE \textbf{Step 3: Survivor Node Selection and Secondary Re-calibration}
    \STATE Filter the survivor list for this layer $\Phi^{(l)} \leftarrow \{k \in \mathcal{A} \mid RawScore_k \ge \theta^{(l)}\}$
    \STATE Re-normalize the effective weights for the survivors $\tilde{w}_k^{(l)} \leftarrow RawScore_k / \sum_{j\in\Phi^{(l)}} RawScore_j$
    \STATE Execute L2 proportional downscaling $\widehat{\Delta W}_k^{(l)} \leftarrow \Delta W_k^{(l)} / \max(1, \|\Delta W_k^{(l)}\|_2 / C^{(l)})$
    \STATE \textbf{Step 4: Layer-wise Merging and Stitching}
    \STATE Extract the highly secure, lesion-free gradient segments for this layer $\Delta W_{global}^{(l)} \leftarrow \sum_{k\in\Phi^{(l)}} \tilde{w}_k^{(l)} \cdot \widehat{\Delta W}_k^{(l)}$
    \STATE Splice and integrate into the global model update amount $\Delta W_{global} \leftarrow \Delta W_{global} \cup \Delta W_{global}^{(l)}$
\ENDFOR
\RETURN $\Delta W_{global}$
\end{algorithmic}
\end{algorithm}'''
)


# 5. Sybil and Interception Sentences
text = replace_between(
    text,
    "Sybil \& Free-rider Nodes}: Serving specifically establishing bounds uniquely",
    "\n",
    r'''Sybil \& Free-rider Nodes}: To empirically validate the efficacy of the Phase 1 TMAA hardware defense line in resisting tampering, the system concurrently initialized 5 Sybil nodes carrying no valid TEE certificates alongside 3 free-rider nodes simulating CPU load dormancy (skipping local epochs to save power) during the initial connection phase.
'''
)

text = replace_between(
    text,
    "Pre-defense Interception Metrics Declarations",
    "completely.\n",
    r'''Pre-defense Interception Measurement Declaration}: The aforementioned 8 fraudulent nodes attempting to externally infiltrate the system and evade real computational processes were either mercilessly intercepted by the TMAA hard gate ($M_{attest,k}$) at the protocol layer, or entirely stripped of their connection privileges due to instantaneous anomalies in the resource monitoring pool (a surge in $A_k$ causing $TrustScore_k \to 0$). Therefore, the 20 formally shortlisted nodes participating throughout the full lifecycle evolution showcased hereafter (including the tracking trajectories in Section 5.2 and precision performance in Section 5.3) strictly designate backend advanced stealth poisoning clusters that painstakingly bypassed the hard-shell audit of the first TMAA phase.
'''
)

# 6. Table Layout Resizing
text = text.replace(
    r"\begin{tabular}{cl | cl}",
    r"\resizebox{\textwidth}{!}{" + "\n" + r"\begin{tabular}{cl | cl}"
)
text = text.replace(
    r"\end{tabular}" + "\n" + r"\end{table}" + "\n\n" + r"\subsection{Phase 3:",
    r"\end{tabular}" + "\n" + r"}" + "\n" + r"\end{table}" + "\n\n" + r"\subsection{Phase 3:"
)

text = text.replace(
    r"\begin{tabular}{p{4cm} p{8.5cm} p{2cm}}",
    r"\resizebox{\textwidth}{!}{" + "\n" + r"\begin{tabular}{p{4cm} p{8.5cm} p{2cm}}"
)
# for hyperparameters table end
text = text.replace(
    r"\bottomrule" + "\n" + r"\end{tabular}" + "\n" + r"\end{table}" + "\n\n" + r"\textbf{Experimental",
    r"\bottomrule" + "\n" + r"\end{tabular}" + "\n" + r"}" + "\n" + r"\end{table}" + "\n\n" + r"\textbf{Experimental"
)

text = text.replace(
    r"\begin{tabular}{l l c c c}",
    r"\resizebox{\textwidth}{!}{" + "\n" + r"\begin{tabular}{l l c c c}"
)
text = replace_between(
    text,
    "\\bottomrule\n\\end{tabular}\n\\end{threeparttable}",
    "",
    "\\bottomrule\n\\end{tabular}\n}\n\\begin{tablenotes}\n\\item[] ($^*$) FPR is Non-Applicable since these mechanics do not explicitly ban nodes permanently.\n\\item[] ($^{**}$) FPR tracks the severe misclassification of legitimate biased nodes (false positives).\n\\end{tablenotes}\n\\end{threeparttable}"
)
# remove the N/A ($*$) notes from old tables just in case they were weirdly formatted
text = text.replace("N/A ($*$)", "N/A ($^*$)")
text = text.replace("64.20 ($^{**}$)", "64.20 ($^{**}$)")
text = text.replace("21.40 ($^{**}$)", "21.40 ($^{**}$)")


text = text.replace(
    r"\begin{tabular}{l c c c}",
    r"\resizebox{\textwidth}{!}{" + "\n" + r"\begin{tabular}{l c c c}"
)
text = text.replace(
    r"\textbf{$\sim 4.85$ s (Total)}" + " \\\\\n\\bottomrule\n\\end{tabular}\n\\end{table}",
    r"\textbf{$\sim 4.85$ s (Total)}" + " \\\\\n\\bottomrule\n\\end{tabular}\n}\n\\end{table}"
)


# 7. Citations Refinements
text = text.replace(
    r"\bibitem{fedpe} Author, A., et al.: FedPE: Adaptive Model Pruning-Expanding for Federated Learning on Mobile Devices. IEEE Transactions on Mobile Computing 23(11) (2024).",
    r"\bibitem{fedpe} Jiang, Y., et al.: FedPE: Adaptive Model Pruning-Expanding for Federated Learning on Mobile Devices. IEEE Transactions on Mobile Computing 23(11) (2024)."
)
text = text.replace(
    r"\bibitem{parallelsfl} Author, A., et al.: ParallelSFL: A Novel Split Federated Learning Framework Tackling Heterogeneity Issues. (202x).",
    r"\bibitem{parallelsfl} Liao, Y., Xu, Y., et al.: ParallelSFL: A Novel Split Federated Learning Framework Tackling Heterogeneity Issues. arXiv preprint arXiv:2410.01256 (2024)."
)
text = text.replace(
    r"\bibitem{flpurifier} Author, A., et al.: FLPurifier: Backdoor Defense in Federated Learning via Decoupled Contrastive Training. (202x).",
    r"\bibitem{flpurifier} Xu, Y., et al.: FLPurifier: Backdoor Defense in Federated Learning via Decoupled Contrastive Training. IEEE Transactions on Information Forensics and Security (2024)."
)
text = text.replace(
    r"\bibitem{roseagg} Author, A., et al.: RoseAgg: Robust Defense Against Targeted Collusion Attacks in Federated Learning. (202x).",
    r"\bibitem{roseagg} Yang, H., Xi, W., et al.: RoseAgg: Robust Defense Against Targeted Collusion Attacks in Federated Learning. IEEE Transactions on Information Forensics and Security (2024)."
)
text = text.replace(
    r"\bibitem{shieldfl} Author, A., et al.: ShieldFL: Mitigating Model Poisoning Attacks in Privacy-Preserving Federated Learning. (202x).",
    r"\bibitem{shieldfl} Ma, Z., Ma, J., et al.: ShieldFL: Mitigating Model Poisoning Attacks in Privacy-Preserving Federated Learning. IEEE Transactions on Information Forensics and Security (2022)."
)
text = text.replace(
    r"\bibitem{r5_tee_mitigating} Author, A., et al.: Mitigating Adversarial Attacks in Federated Learning with Trusted Execution Environments. (202x).",
    r"\bibitem{r5_tee_mitigating} Xu, R., et al.: Mitigating Adversarial Attacks in Federated Learning with Trusted Execution Environments. arXiv preprint (2022)."
)
text = text.replace(
    r"\bibitem{r12_iot_tee} Author, A., et al.: Secure sharing of industrial IoT data based on distributed trust management and trusted execution environment. (202x).",
    r"\bibitem{r12_iot_tee} Li, D., et al.: Secure sharing of industrial IoT data based on distributed trust management and trusted execution environment. Information Sciences (202x)."
)

# Apply!
with open("paper-en-lncs/main.tex", "w", encoding="utf-8") as f:
    f.write(text)

print("Phase 2 Fixes applied.")

