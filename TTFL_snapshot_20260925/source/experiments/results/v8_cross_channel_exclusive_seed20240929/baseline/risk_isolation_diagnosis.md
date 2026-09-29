# Risk isolation diagnosis

Result root: `/data1/lab409/W1lsp0/Pytorch/TTFL_snapshot_20260925/source/experiments/results/v8_cross_channel_exclusive_seed20240929/baseline`

## 1_ttfl_none_seed20240929
- scenario: `none`; rounds read: 30
- isolation reasons: `{"risk_soft_streak": 46}`
- identity × reason: `{"normal:risk_soft_streak": 46}`
- first isolation: `(9, '11', 'normal', 'risk_soft_streak')`
- average channels on isolated records: `{"risk_new": 0.7339008588388481, "probe_risk": 0.0, "grad_risk": 0.5766086731408033, "trigger_risk": 0.0, "pixel_risk": 0.0, "peer_effective": 0.6397968086264836, "soft_hit_count": 1.7608695652173914}`

## 2_ttfl_backdoor_seed20240929
- scenario: `backdoor`; rounds read: 30
- isolation reasons: `{"risk_soft_streak": 45}`
- identity × reason: `{"normal:risk_soft_streak": 45}`
- first isolation: `(9, '16', 'normal', 'risk_soft_streak')`
- average channels on isolated records: `{"risk_new": 0.7469295973651883, "probe_risk": 0.0, "grad_risk": 0.6105819261693536, "trigger_risk": 0.0, "pixel_risk": 0.0, "peer_effective": 0.68605448311488, "soft_hit_count": 1.8888888888888888}`

## 3_ttfl_delayed_backdoor_seed20240929
- scenario: `delayed_backdoor`; rounds read: 30
- isolation reasons: `{"risk_soft_streak": 55}`
- identity × reason: `{"malicious:risk_soft_streak": 2, "normal:risk_soft_streak": 53}`
- first isolation: `(9, '11', 'normal', 'risk_soft_streak')`
- average channels on isolated records: `{"risk_new": 0.7615794649827784, "probe_risk": 0.005207350240722072, "grad_risk": 0.626728095353669, "trigger_risk": 0.0, "pixel_risk": 0.0, "peer_effective": 0.7032795555596237, "soft_hit_count": 1.9272727272727272}`
