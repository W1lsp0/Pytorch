# Risk soft probation paired report

Candidate keeps soft-risk clients in final aggregation during probation while excluding them from the g_root reference set; blacklist and C2 quarantine retain aggregation exclusion. Known-trigger clean_delta, one development seed.

Complete exclusions use `included_layers=0`. Risk-isolation flags are diagnostic state, not proof of aggregation blocking under probation. The JSON retains legacy isolation field names with this meaning.

## backdoor
- final accuracy: 0.5472 → 0.5361 (Δ -0.0111)
- final ASR: 0.0976 → 0.1067 (Δ +0.0091)
- attack-window mean ASR: 0.1892074074074074 → 0.19229259259259257 (Δ 0.003085185185185163)
- attack window: [1, 30]; peak ASR: 0.502777777777778 → 0.497111111111111
- normal exclusions: 64/570 → 33/570 (rate Δ -5.4386%)
- normal risk-isolation/blacklist flags: 62 → 63
- malicious risk-isolation/blacklist flag rounds: [] → []
- malicious complete-exclusion rounds by client: {'1': []} → {'1': []}
- first complete exclusion within attack window by client: {'1': None} → {'1': None}
- excluded before attack by client: {'1': False} → {'1': False}
- reasons baseline: `{"normal:risk_soft_streak": 34, "normal:risk_ema_above_0.90_for_4_rounds": 22, "normal:c2_quarantine": 6}`
- reasons candidate: `{"normal:risk_soft_streak": 43, "normal:c2_drift_combo_for_5_rounds": 19, "normal:c2_quarantine": 1}`

## delayed_backdoor
- final accuracy: 0.5465 → 0.5397 (Δ -0.0068)
- final ASR: 0.1077 → 0.1116 (Δ +0.0039)
- attack-window mean ASR: 0.13316666666666668 → 0.13838333333333336 (Δ 0.005216666666666675)
- attack window: [11, 30]; peak ASR: 0.34055555555555556 → 0.363
- normal exclusions: 56/570 → 38/570 (rate Δ -3.1579%)
- normal risk-isolation/blacklist flags: 54 → 90
- malicious risk-isolation/blacklist flag rounds: [] → []
- malicious complete-exclusion rounds by client: {'1': [19]} → {'1': []}
- first complete exclusion within attack window by client: {'1': 19} → {'1': None}
- excluded before attack by client: {'1': False} → {'1': False}
- reasons baseline: `{"normal:risk_soft_streak": 32, "normal:risk_ema_above_0.90_for_4_rounds": 22}`
- reasons candidate: `{"normal:risk_soft_streak": 61, "normal:c2_quarantine": 12, "normal:c2_drift_combo_for_5_rounds": 17}`

## none
- final accuracy: 0.5588 → 0.5593 (Δ +0.0005)
- final ASR: 0.0660 → 0.0683 (Δ +0.0023)
- attack-window mean ASR: None → None (Δ None)
- attack window: None; peak ASR: None → None
- normal exclusions: 65/600 → 54/600 (rate Δ -1.8333%)
- normal risk-isolation/blacklist flags: 66 → 87
- malicious risk-isolation/blacklist flag rounds: [] → []
- malicious complete-exclusion rounds by client: {} → {}
- first complete exclusion within attack window by client: {} → {}
- excluded before attack by client: {} → {}
- reasons baseline: `{"normal:risk_soft_streak": 45, "normal:c2_drift_combo_for_5_rounds": 21}`
- reasons candidate: `{"normal:risk_soft_streak": 50, "normal:risk_ema_above_0.90_for_4_rounds": 22, "normal:c2_quarantine": 15}`

