# Risk soft probation paired report

Candidate keeps soft-risk clients in final aggregation during probation while excluding them from the g_root reference set; blacklist and C2 quarantine retain aggregation exclusion. Known-trigger clean_delta, one development seed.

Complete exclusions use `included_layers=0`. Risk-isolation flags are diagnostic state, not proof of aggregation blocking under probation. The JSON retains legacy isolation field names with this meaning.

## backdoor
- final accuracy: 0.4821 → 0.4772 (Δ -0.0049)
- final ASR: 0.0941 → 0.1551 (Δ +0.0610)
- attack-window mean ASR: 0.19021111111111114 → 0.20263333333333328 (Δ 0.01242222222222214)
- attack window: [1, 30]; peak ASR: 0.567222222222222 → 0.571111111111111
- normal exclusions: 151/570 → 128/570 (rate Δ -4.0351%)
- normal risk-isolation/blacklist flags: 48 → 66
- malicious risk-isolation/blacklist flag rounds: [21, 22, 23, 24, 25, 26, 27, 28, 29, 30] → [19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30]
- malicious complete-exclusion rounds by client: {'1': [21, 22, 23, 24, 25, 26, 27, 28, 29, 30]} → {'1': [22, 23, 28, 29]}
- first complete exclusion within attack window by client: {'1': 21} → {'1': 22}
- excluded before attack by client: {'1': False} → {'1': False}
- reasons baseline: `{"normal:risk_soft_streak": 48}`
- reasons candidate: `{"normal:risk_soft_streak": 66}`

## delayed_backdoor
- final accuracy: 0.4955 → 0.5225 (Δ +0.0270)
- final ASR: 0.0869 → 0.0761 (Δ -0.0108)
- attack-window mean ASR: 0.11731111111111112 → 0.12546111111111108 (Δ 0.008149999999999963)
- attack window: [11, 30]; peak ASR: 0.20333333333333337 → 0.19866666666666663
- normal exclusions: 151/570 → 146/570 (rate Δ -0.8772%)
- normal risk-isolation/blacklist flags: 53 → 69
- malicious risk-isolation/blacklist flag rounds: [14, 24, 25, 26, 27, 28, 29, 30] → [14, 15, 16, 17, 18, 24, 25, 26, 27, 28, 29, 30]
- malicious complete-exclusion rounds by client: {'1': [14, 15, 16, 17, 18, 19, 20, 24, 25, 26, 27, 28, 29, 30]} → {'1': [16, 17, 18, 19, 20, 26, 27, 28, 30]}
- first complete exclusion within attack window by client: {'1': 14} → {'1': 16}
- excluded before attack by client: {'1': False} → {'1': False}
- reasons baseline: `{"normal:risk_soft_streak": 33, "normal:c2_drift_combo_for_5_rounds": 20}`
- reasons candidate: `{"normal:risk_soft_streak": 69}`

## none
- final accuracy: 0.5028 → 0.5296 (Δ +0.0268)
- final ASR: 0.0824 → 0.0759 (Δ -0.0066)
- attack-window mean ASR: None → None (Δ None)
- attack window: None; peak ASR: None → None
- normal exclusions: 185/600 → 153/600 (rate Δ -5.3333%)
- normal risk-isolation/blacklist flags: 61 → 87
- malicious risk-isolation/blacklist flag rounds: [] → []
- malicious complete-exclusion rounds by client: {} → {}
- first complete exclusion within attack window by client: {} → {}
- excluded before attack by client: {} → {}
- reasons baseline: `{"normal:risk_soft_streak": 61}`
- reasons candidate: `{"normal:risk_soft_streak": 66, "normal:risk_ema_above_0.90_for_4_rounds": 21}`

