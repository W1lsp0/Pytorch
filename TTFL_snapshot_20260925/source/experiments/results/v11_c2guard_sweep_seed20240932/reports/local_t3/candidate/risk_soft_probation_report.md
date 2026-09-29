# Risk soft probation paired report

Candidate keeps soft-risk clients in final aggregation during probation while excluding them from the g_root reference set; blacklist and C2 quarantine retain aggregation exclusion. Known-trigger clean_delta, one development seed.

Complete exclusions use `included_layers=0`. Risk-isolation flags are diagnostic state, not proof of aggregation blocking under probation. The JSON retains legacy isolation field names with this meaning.

## backdoor
- final accuracy: 0.5453 → 0.5402 (Δ -0.0051)
- final ASR: 0.0989 → 0.1020 (Δ +0.0031)
- attack-window mean ASR: 0.1873925925925926 → 0.19223333333333326 (Δ 0.0048407407407406455)
- attack window: [1, 30]; peak ASR: 0.508888888888889 → 0.498111111111111
- normal exclusions: 67/570 → 57/570 (rate Δ -1.7544%)
- normal risk-isolation/blacklist flags: 61 → 83
- malicious risk-isolation/blacklist flag rounds: [] → []
- malicious complete-exclusion rounds by client: {'1': []} → {'1': []}
- first complete exclusion within attack window by client: {'1': None} → {'1': None}
- excluded before attack by client: {'1': False} → {'1': False}
- reasons baseline: `{"normal:risk_soft_streak": 35, "normal:c2_quarantine": 9, "normal:c2_drift_combo_for_5_rounds": 17}`
- reasons candidate: `{"normal:risk_soft_streak": 56, "normal:c2_quarantine": 10, "normal:c2_drift_combo_for_5_rounds": 17}`

## delayed_backdoor
- final accuracy: 0.5423 → 0.5327 (Δ -0.0096)
- final ASR: 0.1050 → 0.1094 (Δ +0.0044)
- attack-window mean ASR: 0.13673888888888888 → 0.13087222222222222 (Δ -0.005866666666666659)
- attack window: [11, 30]; peak ASR: 0.34377777777777796 → 0.31344444444444447
- normal exclusions: 58/570 → 33/570 (rate Δ -4.3860%)
- normal risk-isolation/blacklist flags: 58 → 67
- malicious risk-isolation/blacklist flag rounds: [] → []
- malicious complete-exclusion rounds by client: {'1': [19]} → {'1': [19]}
- first complete exclusion within attack window by client: {'1': 19} → {'1': 19}
- excluded before attack by client: {'1': False} → {'1': False}
- reasons baseline: `{"normal:risk_soft_streak": 37, "normal:c2_drift_combo_for_5_rounds": 21}`
- reasons candidate: `{"normal:risk_soft_streak": 46, "normal:c2_quarantine": 2, "normal:c2_drift_combo_for_5_rounds": 19}`

## none
- final accuracy: 0.5561 → 0.5547 (Δ -0.0014)
- final ASR: 0.0664 → 0.0687 (Δ +0.0022)
- attack-window mean ASR: None → None (Δ None)
- attack window: None; peak ASR: None → None
- normal exclusions: 77/600 → 42/600 (rate Δ -5.8333%)
- normal risk-isolation/blacklist flags: 78 → 90
- malicious risk-isolation/blacklist flag rounds: [] → []
- malicious complete-exclusion rounds by client: {} → {}
- first complete exclusion within attack window by client: {} → {}
- excluded before attack by client: {} → {}
- reasons baseline: `{"normal:risk_soft_streak": 48, "normal:c2_quarantine": 13, "normal:c2_drift_combo_for_5_rounds": 17}`
- reasons candidate: `{"normal:risk_soft_streak": 60, "normal:risk_ema_above_0.90_for_4_rounds": 22, "normal:c2_quarantine": 8}`

