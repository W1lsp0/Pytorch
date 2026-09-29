# V16 guarded probation floor paired audit

V16 exploratory entropy threshold .01 versus V15 threshold .15; same-host and same-seed frozen-source comparisons.

| pair | validation | accuracy | final ASR | attack mean ASR | normal exclusion |
|---|---|---:|---:|---:|---:|
| local_none_original_entropy_s20240936 | validated | 56.78% → 56.67% | 4.08% → 3.44% | n/a → n/a | 11.00% → 0.00% |
| local_none_guarded_entropy_s20240936 | validated | 57.71% → 56.67% | 4.43% → 3.44% | n/a → n/a | 1.17% → 0.00% |
| local_backdoor_original_entropy_s20240936 | validated | 54.46% → 56.45% | 7.12% → 4.18% | 17.56% → 5.80% | 32.28% → 0.00% |
| local_backdoor_guarded_entropy_s20240936 | validated | 56.49% → 56.45% | 5.18% → 4.18% | 5.75% → 5.80% | 9.82% → 0.00% |
| local_delayed_backdoor_original_entropy_s20240936 | validated | 54.82% → 56.64% | 9.93% → 3.87% | 9.50% → 4.83% | 11.40% → 0.00% |
| local_delayed_backdoor_guarded_entropy_s20240936 | validated | 55.82% → 56.64% | 4.58% → 3.87% | 6.55% → 4.83% | 5.09% → 0.00% |
| remote_none_original_entropy_s20240937 | validated | 57.25% → 56.87% | 4.32% → 3.73% | n/a → n/a | 5.17% → 0.00% |
| remote_none_guarded_entropy_s20240937 | validated | 56.82% → 56.87% | 4.82% → 3.73% | n/a → n/a | 3.83% → 0.00% |
| remote_backdoor_original_entropy_s20240937 | validated | 50.62% → 57.04% | 10.58% → 4.70% | 15.56% → 5.80% | 15.26% → 0.00% |
| remote_backdoor_guarded_entropy_s20240937 | validated | 57.67% → 57.04% | 4.28% → 4.70% | 5.08% → 5.80% | 4.21% → 0.00% |
| remote_delayed_backdoor_original_entropy_s20240937 | validated | 56.20% → 57.70% | 8.44% → 4.17% | 9.00% → 5.16% | 4.39% → 0.00% |
| remote_delayed_backdoor_guarded_entropy_s20240937 | validated | 57.13% → 57.70% | 4.52% → 4.17% | 4.29% → 5.16% | 4.04% → 0.00% |
