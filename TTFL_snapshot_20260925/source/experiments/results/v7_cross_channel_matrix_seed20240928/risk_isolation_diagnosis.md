# Risk isolation diagnosis

Result root: `/data1/lab409/W1lsp0/Pytorch/TTFL_snapshot_20260925/source/experiments/results/v7_cross_channel_matrix_seed20240928`

## 1_ttfl_none_seed20240928
- scenario: `none`; rounds read: 30
- isolation reasons: `{"risk_soft_streak": 3}`
- identity × reason: `{"normal:risk_soft_streak": 3}`
- first isolation: `(10, '16', 'normal', 'risk_soft_streak')`
- average channels on isolated records: `{"risk_new": 0.8035931772944788, "probe_risk": 0.0, "grad_risk": 0.715420545568553, "trigger_risk": 0.0, "pixel_risk": 0.0, "peer_effective": 0.8053244320743794, "soft_hit_count": 2.0}`

## 2_ttfl_backdoor_seed20240928
- scenario: `backdoor`; rounds read: 30
- isolation reasons: `{"risk_soft_streak": 3}`
- identity × reason: `{"normal:risk_soft_streak": 3}`
- first isolation: `(10, '16', 'normal', 'risk_soft_streak')`
- average channels on isolated records: `{"risk_new": 0.8019284661251905, "probe_risk": 0.0, "grad_risk": 0.6161372196126046, "trigger_risk": 0.0, "pixel_risk": 0.0, "peer_effective": 0.7331841760135432, "soft_hit_count": 2.0}`

## 3_ttfl_delayed_backdoor_seed20240928
- scenario: `delayed_backdoor`; rounds read: 30
- isolation reasons: `{"risk_soft_streak": 1}`
- identity × reason: `{"malicious:risk_soft_streak": 1}`
- first isolation: `(17, '1', 'malicious', 'risk_soft_streak')`
- average channels on isolated records: `{"risk_new": 0.8294319266786948, "probe_risk": 0.0, "grad_risk": 0.2043881927917063, "trigger_risk": 0.0, "pixel_risk": 0.0, "peer_effective": 0.4451910573279585, "soft_hit_count": 2.0}`
