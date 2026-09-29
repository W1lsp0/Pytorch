# Risk isolation diagnosis

Result root: `/data1/lab409/W1lsp0/Pytorch/TTFL_snapshot_20260925/source/experiments/results/v8_cross_channel_exclusive_seed20240929/candidate`

## 1_ttfl_none_seed20240929
- scenario: `none`; rounds read: 30
- isolation reasons: `{"risk_soft_streak": 5}`
- identity × reason: `{"normal:risk_soft_streak": 5}`
- first isolation: `(9, '16', 'normal', 'risk_soft_streak')`
- average channels on isolated records: `{"risk_new": 0.8451102083468888, "probe_risk": 0.0, "grad_risk": 0.9215170388717585, "trigger_risk": 0.0, "pixel_risk": 0.0, "peer_effective": 0.8927173118416187, "soft_hit_count": 2.0}`

## 2_ttfl_backdoor_seed20240929
- scenario: `backdoor`; rounds read: 30
- isolation reasons: `{"risk_soft_streak": 3}`
- identity × reason: `{"normal:risk_soft_streak": 3}`
- first isolation: `(9, '16', 'normal', 'risk_soft_streak')`
- average channels on isolated records: `{"risk_new": 0.8221604231503331, "probe_risk": 0.0, "grad_risk": 0.8705341704660033, "trigger_risk": 0.0, "pixel_risk": 0.0, "peer_effective": 0.8768881543610654, "soft_hit_count": 2.0}`

## 3_ttfl_delayed_backdoor_seed20240929
- scenario: `delayed_backdoor`; rounds read: 30
- isolation reasons: `{"risk_soft_streak": 3}`
- identity × reason: `{"normal:risk_soft_streak": 3}`
- first isolation: `(9, '16', 'normal', 'risk_soft_streak')`
- average channels on isolated records: `{"risk_new": 0.8353504039182497, "probe_risk": 0.0, "grad_risk": 0.8785760566680075, "trigger_risk": 0.0, "pixel_risk": 0.0, "peer_effective": 0.9269765044445396, "soft_hit_count": 2.0}`
