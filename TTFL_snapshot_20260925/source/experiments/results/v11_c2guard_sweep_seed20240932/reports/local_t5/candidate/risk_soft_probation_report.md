# Risk soft probation paired report

Candidate keeps soft-risk clients in final aggregation during probation while excluding them from the g_root reference set; blacklist and C2 quarantine retain aggregation exclusion. Known-trigger clean_delta, one development seed.

Complete exclusions use `included_layers=0`. Risk-isolation flags are diagnostic state, not proof of aggregation blocking under probation. The JSON retains legacy isolation field names with this meaning.

## backdoor
- final accuracy: 0.5453 → 0.5319 (Δ -0.0134)
- final ASR: 0.0989 → 0.1103 (Δ +0.0114)
- attack-window mean ASR: 0.1873925925925926 → 0.19207037037037036 (Δ 0.004677777777777753)
- attack window: [1, 30]; peak ASR: 0.508888888888889 → 0.504777777777778
- normal exclusions: 67/570 → 24/570 (rate Δ -7.5439%)
- normal risk-isolation/blacklist flags: 61 → 70
- malicious risk-isolation/blacklist flag rounds: [] → []
- malicious complete-exclusion rounds by client: {'1': []} → {'1': []}
- first complete exclusion within attack window by client: {'1': None} → {'1': None}
- excluded before attack by client: {'1': False} → {'1': False}
- reasons baseline: `{"normal:risk_soft_streak": 35, "normal:c2_quarantine": 9, "normal:c2_drift_combo_for_5_rounds": 17}`
- reasons candidate: `{"normal:risk_soft_streak": 48, "normal:risk_ema_above_0.90_for_4_rounds": 22}`

## delayed_backdoor
- final accuracy: 0.5423 → 0.5393 (Δ -0.0030)
- final ASR: 0.1050 → 0.1181 (Δ +0.0131)
- attack-window mean ASR: 0.13673888888888888 → 0.13899444444444448 (Δ 0.002255555555555594)
- attack window: [11, 30]; peak ASR: 0.34377777777777796 → 0.335111111111111
- normal exclusions: 58/570 → 27/570 (rate Δ -5.4386%)
- normal risk-isolation/blacklist flags: 58 → 67
- malicious risk-isolation/blacklist flag rounds: [] → []
- malicious complete-exclusion rounds by client: {'1': [19]} → {'1': [19]}
- first complete exclusion within attack window by client: {'1': 19} → {'1': 19}
- excluded before attack by client: {'1': False} → {'1': False}
- reasons baseline: `{"normal:risk_soft_streak": 37, "normal:c2_drift_combo_for_5_rounds": 21}`
- reasons candidate: `{"normal:risk_soft_streak": 42, "normal:risk_ema_above_0.90_for_4_rounds": 22, "normal:c2_quarantine": 3}`

## none
- final accuracy: 0.5561 → 0.5533 (Δ -0.0028)
- final ASR: 0.0664 → 0.0703 (Δ +0.0039)
- attack-window mean ASR: None → None (Δ None)
- attack window: None; peak ASR: None → None
- normal exclusions: 77/600 → 50/600 (rate Δ -4.5000%)
- normal risk-isolation/blacklist flags: 78 → 91
- malicious risk-isolation/blacklist flag rounds: [] → []
- malicious complete-exclusion rounds by client: {} → {}
- first complete exclusion within attack window by client: {} → {}
- excluded before attack by client: {} → {}
- reasons baseline: `{"normal:risk_soft_streak": 48, "normal:c2_quarantine": 13, "normal:c2_drift_combo_for_5_rounds": 17}`
- reasons candidate: `{"normal:risk_soft_streak": 45, "normal:risk_ema_above_0.90_for_4_rounds": 22, "normal:risk_soft_isolation_for_8_rounds": 19, "normal:c2_quarantine": 5}`

