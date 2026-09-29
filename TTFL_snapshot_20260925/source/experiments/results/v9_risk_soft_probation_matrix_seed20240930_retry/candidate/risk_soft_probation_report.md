# Risk soft probation paired report

One switch: risk soft streak remains an audited/attenuated probation state; blacklist and C2 quarantine retain aggregation exclusion. Known-trigger clean_delta, one development seed.

Complete exclusions use `included_layers=0`. Risk-isolation flags are diagnostic state, not proof of aggregation blocking under probation. The JSON retains legacy isolation field names with this meaning.

## backdoor
- final accuracy: 0.5404 → 0.5374 (Δ -0.0030)
- final ASR: 0.1066 → 0.1200 (Δ +0.0134)
- attack-window mean ASR: 0.18951481481481477 → 0.1911740740740741 (Δ 0.0016592592592593325)
- attack window: [1, 30]; peak ASR: 0.44733333333333336 → 0.444111111111111
- normal exclusions: 24/570 → 0/570 (rate Δ -4.2105%)
- normal risk-isolation/blacklist flags: 25 → 22
- malicious risk-isolation/blacklist flag rounds: [] → []
- malicious complete-exclusion rounds by client: {'1': []} → {'1': []}
- first complete exclusion within attack window by client: {'1': None} → {'1': None}
- excluded before attack by client: {'1': False} → {'1': False}
- reasons baseline: `{"normal:c2_quarantine": 4, "normal:risk_soft_streak": 3, "normal:c2_drift_combo_for_5_rounds": 18}`
- reasons candidate: `{"normal:risk_soft_streak": 22}`

## delayed_backdoor
- final accuracy: 0.5472 → 0.5446 (Δ -0.0026)
- final ASR: 0.1161 → 0.1097 (Δ -0.0064)
- attack-window mean ASR: 0.12788333333333332 → 0.1237277777777778 (Δ -0.0041555555555555235)
- attack window: [11, 30]; peak ASR: 0.2027777777777778 → 0.1992222222222222
- normal exclusions: 21/570 → 0/570 (rate Δ -3.6842%)
- normal risk-isolation/blacklist flags: 21 → 3
- malicious risk-isolation/blacklist flag rounds: [] → []
- malicious complete-exclusion rounds by client: {'1': [19]} → {'1': [19]}
- first complete exclusion within attack window by client: {'1': 19} → {'1': 19}
- excluded before attack by client: {'1': False} → {'1': False}
- reasons baseline: `{"normal:risk_soft_streak": 5, "normal:c2_quarantine": 16}`
- reasons candidate: `{"normal:risk_soft_streak": 3}`

## none
- final accuracy: 0.5584 → 0.5620 (Δ +0.0036)
- final ASR: 0.0621 → 0.0552 (Δ -0.0069)
- attack-window mean ASR: None → None (Δ None)
- attack window: None; peak ASR: None → None
- normal exclusions: 18/600 → 17/600 (rate Δ -0.1667%)
- normal risk-isolation/blacklist flags: 19 → 20
- malicious risk-isolation/blacklist flag rounds: [] → []
- malicious complete-exclusion rounds by client: {} → {}
- first complete exclusion within attack window by client: {} → {}
- excluded before attack by client: {} → {}
- reasons baseline: `{"normal:c2_quarantine": 1, "normal:risk_soft_streak": 1, "normal:c2_drift_combo_for_5_rounds": 17}`
- reasons candidate: `{"normal:c2_quarantine": 4, "normal:risk_soft_streak": 3, "normal:c2_drift_combo_for_5_rounds": 13}`

