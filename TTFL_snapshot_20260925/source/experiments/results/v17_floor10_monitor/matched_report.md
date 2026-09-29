# V17 guarded probation floor paired audit

V17 exploratory entropy threshold .01 versus V15 threshold .15; same-host and same-seed frozen-source comparisons.

| pair | validation | accuracy | final ASR | attack mean ASR | normal exclusion |
|---|---|---:|---:|---:|---:|
| local_none_entropy01_floor10_s20240936 | validated | 56.67% → 56.95% | 3.44% → 4.24% | n/a → n/a | 0.00% → 7.33% |
| local_backdoor_entropy01_floor10_s20240936 | validated | 56.45% → 56.81% | 4.18% → 4.27% | 5.80% → 5.87% | 0.00% → 9.47% |
| local_delayed_backdoor_entropy01_floor10_s20240936 | validated | 56.64% → 56.92% | 3.87% → 3.93% | 4.83% → 5.19% | 0.00% → 7.02% |
| remote_none_entropy01_floor10_s20240937 | validated | 56.87% → 57.51% | 3.73% → 4.37% | n/a → n/a | 0.00% → 4.67% |
| remote_backdoor_entropy01_floor10_s20240937 | validated | 57.04% → 57.09% | 4.70% → 4.48% | 5.80% → 5.70% | 0.00% → 4.21% |
| remote_delayed_backdoor_entropy01_floor10_s20240937 | validated | 57.70% → 57.21% | 4.17% → 4.19% | 5.16% → 5.07% | 0.00% → 3.33% |
