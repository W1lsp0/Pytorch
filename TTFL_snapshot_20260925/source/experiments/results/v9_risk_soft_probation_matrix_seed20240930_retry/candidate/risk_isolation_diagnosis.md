# Risk isolation diagnosis

Result root: `/data1/lab409/W1lsp0/Pytorch/TTFL_snapshot_20260925/source/experiments/results/v9_risk_soft_probation_matrix_seed20240930_retry/candidate`

## 4_ttfl_none_seed20240930
- scenario: `none`; rounds read: 30
- isolation reasons: `{"c2_quarantine": 4, "risk_soft_streak": 3, "c2_drift_combo_for_5_rounds": 1}`
- identity × reason: `{"normal:c2_drift_combo_for_5_rounds": 1, "normal:c2_quarantine": 4, "normal:risk_soft_streak": 3}`
- first isolation: `(13, '11', 'normal', 'c2_quarantine')`
- average channels on isolated records: `{"risk_new": 0.571063326782967, "probe_risk": 0.33331046688640986, "grad_risk": 0.434903837528195, "trigger_risk": 0.0, "pixel_risk": 0.0, "peer_effective": 0.4646309639972735, "soft_hit_count": 2.25}`

## 5_ttfl_backdoor_seed20240930
- scenario: `backdoor`; rounds read: 30
- isolation reasons: `{"risk_soft_streak": 22}`
- identity × reason: `{"normal:risk_soft_streak": 22}`
- first isolation: `(9, '16', 'normal', 'risk_soft_streak')`
- average channels on isolated records: `{"risk_new": 0.6347655692775624, "probe_risk": 0.0, "grad_risk": 0.523118890477673, "trigger_risk": 0.0, "pixel_risk": 0.0, "peer_effective": 0.5746536627207175, "soft_hit_count": 1.9090909090909092}`

## 6_ttfl_delayed_backdoor_seed20240930
- scenario: `delayed_backdoor`; rounds read: 30
- isolation reasons: `{"risk_soft_streak": 3}`
- identity × reason: `{"normal:risk_soft_streak": 3}`
- first isolation: `(11, '16', 'normal', 'risk_soft_streak')`
- average channels on isolated records: `{"risk_new": 0.6546456726321731, "probe_risk": 0.0, "grad_risk": 0.4708618562420517, "trigger_risk": 0.0, "pixel_risk": 0.0, "peer_effective": 0.5908618562420517, "soft_hit_count": 2.0}`
