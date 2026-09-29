# V15 guarded probation floor paired audit

V15 guarded probation floor: floor=.25 applies only when previous low-entropy probe risk is below .5.

| pair | validation | accuracy | final ASR | attack mean ASR | normal exclusion |
|---|---|---:|---:|---:|---:|
| local_none_original_guarded_s20240936 | validated | 56.78% → 57.71% | 4.08% → 4.43% | n/a → n/a | 11.00% → 1.17% |
| local_none_floor_guarded_s20240936 | validated | 57.83% → 57.71% | 4.50% → 4.43% | n/a → n/a | 0.83% → 1.17% |
| local_backdoor_original_guarded_s20240936 | validated | 54.46% → 56.49% | 7.12% → 5.18% | 17.56% → 5.75% | 32.28% → 9.82% |
| local_backdoor_floor_guarded_s20240936 | validated | 56.59% → 56.49% | 4.51% → 5.18% | 6.53% → 5.75% | 0.70% → 9.82% |
| local_delayed_backdoor_original_guarded_s20240936 | validated | 54.82% → 55.82% | 9.93% → 4.58% | 9.50% → 6.55% | 11.40% → 5.09% |
| local_delayed_backdoor_floor_guarded_s20240936 | validated | 57.62% → 55.82% | 4.29% → 4.58% | 5.01% → 6.55% | 0.88% → 5.09% |
| remote_none_original_guarded_s20240937 | validated | 57.25% → 56.82% | 4.32% → 4.82% | n/a → n/a | 5.17% → 3.83% |
| remote_none_floor_guarded_s20240937 | validated | 57.81% → 56.82% | 4.18% → 4.82% | n/a → n/a | 1.67% → 3.83% |
| remote_backdoor_original_guarded_s20240937 | validated | 50.62% → 57.67% | 10.58% → 4.28% | 15.56% → 5.08% | 15.26% → 4.21% |
| remote_backdoor_floor_guarded_s20240937 | validated | 56.61% → 57.67% | 3.88% → 4.28% | 4.73% → 5.08% | 2.63% → 4.21% |
| remote_delayed_backdoor_original_guarded_s20240937 | validated | 56.20% → 57.13% | 8.44% → 4.52% | 9.00% → 4.29% | 4.39% → 4.04% |
| remote_delayed_backdoor_floor_guarded_s20240937 | validated | 57.68% → 57.13% | 4.21% → 4.52% | 4.46% → 4.29% | 4.04% → 4.04% |
