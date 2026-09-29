# Risk soft probation paired report

Candidate keeps soft-risk clients in final aggregation during probation while excluding them from the g_root reference set; blacklist and C2 quarantine retain aggregation exclusion. Known-trigger clean_delta, one development seed.

Complete exclusions use `included_layers=0`. Risk-isolation flags are diagnostic state, not proof of aggregation blocking under probation. The JSON retains legacy isolation field names with this meaning.

## backdoor
- final accuracy: 0.5453 → 0.5099 (Δ -0.0354)
- final ASR: 0.0989 → 0.1350 (Δ +0.0361)
- attack-window mean ASR: 0.1873925925925926 → 0.19205185185185192 (Δ 0.004659259259259307)
- attack window: [1, 30]; peak ASR: 0.508888888888889 → 0.5023333333333332
- normal exclusions: 67/570 → 66/570 (rate Δ -0.1754%)
- normal risk-isolation/blacklist flags: 61 → 91
- malicious risk-isolation/blacklist flag rounds: [] → [25, 26, 27, 28, 29, 30]
- malicious complete-exclusion rounds by client: {'1': []} → {'1': []}
- first complete exclusion within attack window by client: {'1': None} → {'1': None}
- excluded before attack by client: {'1': False} → {'1': False}
- reasons baseline: `{"normal:risk_soft_streak": 35, "normal:c2_quarantine": 9, "normal:c2_drift_combo_for_5_rounds": 17}`
- reasons candidate: `{"normal:risk_soft_streak": 42, "normal:c2_quarantine": 9, "normal:c2_drift_combo_for_5_rounds": 40}`

## delayed_backdoor
- final accuracy: 0.5423 → 0.5319 (Δ -0.0104)
- final ASR: 0.1050 → 0.1138 (Δ +0.0088)
- attack-window mean ASR: 0.13673888888888888 → 0.14856666666666665 (Δ 0.01182777777777777)
- attack window: [11, 30]; peak ASR: 0.34377777777777796 → 0.389111111111111
- normal exclusions: 58/570 → 54/570 (rate Δ -0.7018%)
- normal risk-isolation/blacklist flags: 58 → 110
- malicious risk-isolation/blacklist flag rounds: [] → []
- malicious complete-exclusion rounds by client: {'1': [19]} → {'1': [19]}
- first complete exclusion within attack window by client: {'1': 19} → {'1': 19}
- excluded before attack by client: {'1': False} → {'1': False}
- reasons baseline: `{"normal:risk_soft_streak": 37, "normal:c2_drift_combo_for_5_rounds": 21}`
- reasons candidate: `{"normal:risk_soft_streak": 65, "normal:risk_ema_above_0.90_for_4_rounds": 22, "normal:c2_quarantine": 5, "normal:risk_soft_isolation_for_8_rounds": 18}`

## none
- final accuracy: 0.5561 → 0.5435 (Δ -0.0126)
- final ASR: 0.0664 → 0.0741 (Δ +0.0077)
- attack-window mean ASR: None → None (Δ None)
- attack window: None; peak ASR: None → None
- normal exclusions: 77/600 → 42/600 (rate Δ -5.8333%)
- normal risk-isolation/blacklist flags: 78 → 85
- malicious risk-isolation/blacklist flag rounds: [] → []
- malicious complete-exclusion rounds by client: {} → {}
- first complete exclusion within attack window by client: {} → {}
- excluded before attack by client: {} → {}
- reasons baseline: `{"normal:risk_soft_streak": 48, "normal:c2_quarantine": 13, "normal:c2_drift_combo_for_5_rounds": 17}`
- reasons candidate: `{"normal:risk_soft_streak": 62, "normal:c2_drift_combo_for_5_rounds": 19, "normal:c2_quarantine": 4}`

