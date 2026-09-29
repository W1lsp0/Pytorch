# V12 配对审计

Development results. Four switches change together; not a single-factor guard ablation. Historical seed 20240932 uses a different source revision. Seed 20240933 pairs must match host, Python path, training source, initialization, partitions, and attack schedule. No independent multi-seed success claim. Failed/incomplete runs excluded.

| 条件 | 校验 | 准确率 基线→候选 | 最终 ASR | 攻击窗口平均 ASR | 正常完全排除率 |
|---|---|---:|---:|---:|---:|
| local_none_s20240933 | validated | 48.22% → 49.26% | 13.09% → 18.89% | n/a → n/a | 42.17% → 22.33% |
| local_backdoor_s20240933 | validated | 49.36% → 44.36% | 12.78% → 19.84% | 20.15% → 17.97% | 31.23% → 47.37% |
| local_delayed_s20240933 | validated | 44.05% → 53.68% | 6.84% → 14.94% | 14.41% → 10.59% | 48.77% → 5.44% |
| remote_none_s20240933 | validated | 51.54% → 53.57% | 10.37% → 10.88% | n/a → n/a | 39.33% → 20.50% |
| remote_backdoor_s20240933 | validated | 51.24% → 50.47% | 13.33% → 19.18% | 19.46% → 14.37% | 25.26% → 7.02% |
| remote_delayed_s20240933 | validated | 50.22% → 48.92% | 11.58% → 18.78% | 14.91% → 15.38% | 46.32% → 25.44% |
| local_historical_none_s20240932 | historical_reference | 55.61% → 55.32% | 6.64% → 7.24% | n/a → n/a | 12.83% → 7.00% |
| local_historical_backdoor_s20240932 | historical_reference | 54.53% → 54.40% | 9.89% → 8.39% | 18.74% → 11.70% | 11.75% → 6.67% |
| local_historical_delayed_s20240932 | historical_reference | 54.23% → 54.66% | 10.50% → 8.13% | 13.67% → 9.29% | 10.18% → 5.96% |
