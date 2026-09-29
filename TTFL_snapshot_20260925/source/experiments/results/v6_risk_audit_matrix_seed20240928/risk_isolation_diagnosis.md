# Risk isolation diagnosis

Result root: `/data1/lab409/W1lsp0/Pytorch/TTFL_snapshot_20260925/source/experiments/results/v6_risk_audit_matrix_seed20240928`

## 1_ttfl_none_seed20240928
- scenario: `none`; rounds read: 30
- isolation reasons: `{"risk_soft_streak": 45, "c2_quarantine": 1}`
- identity × reason: `{"normal:c2_quarantine": 1, "normal:risk_soft_streak": 45}`
- first isolation: `(9, '13', 'normal', 'risk_soft_streak')`
- average channels on isolated records: `{"risk_new": 0.7294073694813691, "probe_risk": 0.009779574599226097, "grad_risk": 0.6025052980699106, "trigger_risk": 0.0, "pixel_risk": 0.0, "peer_effective": 0.6528507185916826, "soft_hit_count": 1.8478260869565217}`

## 2_ttfl_backdoor_seed20240928
- scenario: `backdoor`; rounds read: 30
- isolation reasons: `{"risk_soft_streak": 43}`
- identity × reason: `{"normal:risk_soft_streak": 43}`
- first isolation: `(9, '16', 'normal', 'risk_soft_streak')`
- average channels on isolated records: `{"risk_new": 0.7422609345816188, "probe_risk": 0.001417760743906659, "grad_risk": 0.6303861858371518, "trigger_risk": 0.0, "pixel_risk": 0.0, "peer_effective": 0.6986748904412, "soft_hit_count": 1.9767441860465116}`

## 3_ttfl_delayed_backdoor_seed20240928
- scenario: `delayed_backdoor`; rounds read: 30
- isolation reasons: `{"risk_soft_streak": 45}`
- identity × reason: `{"malicious:risk_soft_streak": 1, "normal:risk_soft_streak": 44}`
- first isolation: `(9, '16', 'normal', 'risk_soft_streak')`
- average channels on isolated records: `{"risk_new": 0.6987675081807971, "probe_risk": 0.0006801016400114334, "grad_risk": 0.5701975886792353, "trigger_risk": 0.0, "pixel_risk": 0.0, "peer_effective": 0.6079549535288833, "soft_hit_count": 1.9555555555555555}`
