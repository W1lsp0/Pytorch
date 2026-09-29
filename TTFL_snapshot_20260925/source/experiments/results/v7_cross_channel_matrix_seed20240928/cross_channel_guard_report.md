# Cross-channel guard paired report

Baseline: `/data1/lab409/W1lsp0/Pytorch/TTFL_snapshot_20260925/source/experiments/results/v6_risk_audit_matrix_seed20240928`
Candidate: `/data1/lab409/W1lsp0/Pytorch/TTFL_snapshot_20260925/source/experiments/results/v7_cross_channel_matrix_seed20240928`

Two intervention sites: guarded soft gate with soft_strong bypass retained, and guarded C2 quarantine hit. Temporal/spectral/sign are extra evidence channels, not proven statistically independent. Default guard remains off; known-trigger clean_delta study, one seed per report.

Normal exclusions use included_layers=0; explicit isolation is reported separately. Attack-window endpoints come from each manifest; stop is exclusive.

## backdoor
- final accuracy: 0.5504 → 0.5530 (Δ +0.0026)
- final ASR: 0.1054 → 0.1086 (Δ +0.0031)
- attack-window rounds: [1, 30]; peak ASR: 0.437888888888889 → 0.446888888888889
- explicit normal isolations: 43 → 3
- malicious isolated rounds: [] → []
- attack-window mean ASR: 0.2047037037037037 → 0.20293333333333333 (Δ -0.0017703703703703666)
- normal exclusions: 43/570 → 17/570 (Δ -26; rate Δ -4.5614%)
- max normal excluded in one round: 2 → 2
- first malicious isolation: None → None
- reasons baseline: `{"normal:risk_soft_streak": 43}`
- reasons candidate: `{"normal:risk_soft_streak": 3}`

## delayed_backdoor
- final accuracy: 0.5582 → 0.5580 (Δ -0.0002)
- final ASR: 0.0964 → 0.0983 (Δ +0.0019)
- attack-window rounds: [11, 30]; peak ASR: 0.34622222222222204 → 0.320111111111111
- explicit normal isolations: 44 → 0
- malicious isolated rounds: [17] → [17]
- attack-window mean ASR: 0.14149444444444442 → 0.13978333333333332 (Δ -0.0017111111111111077)
- normal exclusions: 44/570 → 21/570 (Δ -23; rate Δ -4.0351%)
- max normal excluded in one round: 3 → 2
- first malicious isolation: 17 → 17
- reasons baseline: `{"normal:risk_soft_streak": 44}`
- reasons candidate: `{}`

## none
- final accuracy: 0.5678 → 0.5718 (Δ +0.0040)
- final ASR: 0.0618 → 0.0667 (Δ +0.0049)
- attack-window rounds: None; peak ASR: None → None
- explicit normal isolations: 46 → 3
- malicious isolated rounds: [] → []
- attack-window mean ASR: None → None (Δ None)
- normal exclusions: 46/600 → 17/600 (Δ -29; rate Δ -4.8333%)
- max normal excluded in one round: 3 → 2
- first malicious isolation: None → None
- reasons baseline: `{"normal:risk_soft_streak": 45, "normal:c2_quarantine": 1}`
- reasons candidate: `{"normal:risk_soft_streak": 3}`
