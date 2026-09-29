# Cross-channel guard paired report

Baseline: `/data1/lab409/W1lsp0/Pytorch/TTFL_snapshot_20260925/source/experiments/results/v8_cross_channel_exclusive_seed20240929/baseline`
Candidate: `/data1/lab409/W1lsp0/Pytorch/TTFL_snapshot_20260925/source/experiments/results/v8_cross_channel_exclusive_seed20240929/candidate`

Two intervention sites: guarded soft gate with soft_strong bypass retained, and guarded C2 quarantine hit. Temporal/spectral/sign are extra evidence channels, not proven statistically independent. Default guard remains off; known-trigger clean_delta study, one seed per report.

Normal exclusions use included_layers=0; explicit isolation is reported separately. Attack-window endpoints come from each manifest; stop is exclusive.

## backdoor
- final accuracy: 0.5446 → 0.5372 (Δ -0.0074)
- final ASR: 0.1309 → 0.1400 (Δ +0.0091)
- attack-window rounds: [1, 30]; peak ASR: 0.646222222222222 → 0.651222222222222
- explicit normal isolations: 45 → 3
- malicious isolated rounds: [] → []
- attack-window mean ASR: 0.20687407407407404 → 0.21052222222222217 (Δ 0.0036481481481481226)
- normal exclusions: 45/570 → 26/570 (Δ -19; rate Δ -3.3333%)
- max normal excluded in one round: 3 → 2
- first malicious isolation: None → None
- reasons baseline: `{"normal:risk_soft_streak": 45}`
- reasons candidate: `{"normal:risk_soft_streak": 3}`

## delayed_backdoor
- final accuracy: 0.5444 → 0.5491 (Δ +0.0047)
- final ASR: 0.1082 → 0.1264 (Δ +0.0182)
- attack-window rounds: [11, 30]; peak ASR: 0.2407777777777779 → 0.2806666666666666
- explicit normal isolations: 53 → 3
- malicious isolated rounds: [16, 30] → []
- attack-window mean ASR: 0.1461 → 0.15208888888888888 (Δ 0.005988888888888877)
- normal exclusions: 75/570 → 18/570 (Δ -57; rate Δ -10.0000%)
- max normal excluded in one round: 5 → 2
- first malicious isolation: 16 → None
- reasons baseline: `{"normal:risk_soft_streak": 53}`
- reasons candidate: `{"normal:risk_soft_streak": 3}`

## none
- final accuracy: 0.5670 → 0.5711 (Δ +0.0041)
- final ASR: 0.0828 → 0.0671 (Δ -0.0157)
- attack-window rounds: None; peak ASR: None → None
- explicit normal isolations: 46 → 5
- malicious isolated rounds: [] → []
- attack-window mean ASR: None → None (Δ None)
- normal exclusions: 46/600 → 21/600 (Δ -25; rate Δ -4.1667%)
- max normal excluded in one round: 4 → 2
- first malicious isolation: None → None
- reasons baseline: `{"normal:risk_soft_streak": 46}`
- reasons candidate: `{"normal:risk_soft_streak": 5}`
