# Reproduction contract for the revised ISPA manuscript

The manuscript reports existing protocol-v2 **development** runs. No training was performed while preparing this revision. No synthetic results are included. Group values are means and sample standard deviations of two seed-level observations, not statistics across communication rounds.

## Experimental profiles

| Profile | Runs | Methods | Attacks | Probe assumption |
|---|---:|---|---|---|
| K0 / standard | 24 | FedAvg, local FLTrust, collapsed decision state, TTFL | none, persistent (1–30), delayed (11–30) | Known templates disabled; heavy-probe rotation modulus 5 with priority probes |
| K1 / known trigger | 12 | collapsed decision state, TTFL | same three scenarios | Known templates enabled; heavy-probe rotation modulus 1 |
| Recovery | 8 | same four methods as K0 | active in rounds 3–9; clean from 10 | K0 probe settings |

All runs use 20 clients, 30 rounds, one local epoch, two seeds (20240925 and 20240926), a disjoint 500-image reference from CIFAR-10 training data, and no shared client training pool. One client (ID 1) attacks in attacked scenarios. No-attack triggered evaluation is a background target-hit measurement. This profile must not be relabeled as 30% mixed attacks or five repetitions.

## Numerical checks and provenance

`../revision_tools/build_evidence.py` validates run counts, manifests, final-round agreement, attack-window arithmetic, group means/SDs, matched initial model hashes, disjoint training indices, and matched partition indices. It exports the supplied run-level numerical records and their source hashes. For K1 attacker-admission figures it reads `round_metrics.jsonl`; missing blacklisted rows are filled only where the archived report explicitly records same-round blacklist evidence.

The local snapshot does not contain all original remote console logs. Earlier log-based validations, recovered exclusions, and process-shutdown exceptions are preserved as archived provenance. Recomputing a statistic is not independent verification that training was correctly performed. Before final validation, retrieve or regenerate complete raw logs and freeze the code/configuration.

## Metric definitions

- Final accuracy and ASR use round 30, never separate best checkpoints.
- ASR excludes test examples whose original class is the target, leaving 9,000 examples for the stated CIFAR-10 attack.
- Attack-window mean/peak is restricted to the actual active poisoning rounds.
- Benign complete exclusion means `included_layers == 0`, divided by all configured benign client-rounds. The denominator is 20 benign clients in no-attack runs and 19 in attacked runs.
- Ever excluded counts distinct benign identities excluded at least once; it is not a client-round average or permanent-ban FPR.
- First attacker exclusion is the first post-start zero-admission round, with pre-existing exclusion flagged separately. It is not the first SUSPECT label.
- Tensor admission fraction is `included_layers / layer_count`. It does not measure score-normalized aggregation mass.
- A recovery latency requires an actual restriction preceding the clean period and a later return. Never-excluded clients do not have latency zero; unobserved recovery remains unobserved.

## Method version

The frozen policy source and SHA-256 are in `policy_source.json`. `../revision_tools/policy_reference.py` is an AST extraction of its `TrustScoreManager`, with database configuration and persistence removed. Numerical decision expressions are preserved, including compound C1/C2 routes, decay counters, peer corroboration, and calibration constants. `policy_parameters.json` exposes literal scalar defaults. The extraction is an explanatory artifact, not a replacement implementation validated by the archived experiments.

Other implementation functions are in the `work/` source snapshot beside each original run manifest: `server/strategy.py`, `server/contribution.py`, `server/sensitivity.py`, `Client/model.py`, `Client/engine.py`, and `data_protocol.py`. In particular, the collapsed state is H(1−R), the saved RawScore uses prior H/R, current soft isolation is applied before aggregation, and new blacklist membership is checked at subsequent admission. None of these behaviors should be silently changed while retaining the old results.

## Figure contract

The results figure compares actual per-seed learning trajectories; the probe figure compares final and attack-window ASR against benign exclusion; the participation figure shows actual admitted tensors for the attacker. These are two-column figures at approximately 7.16 inches, exported to vector PDF and editable SVG plus PNG previews. Line styles and markers supplement color. No confidence intervals or significance markers are inferred from two seeds. The conceptual flowchart is drawn natively in LaTeX and contains no experimental data.
