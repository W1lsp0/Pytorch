# V14 probation weight paired audit

V14 floor ablation changes only probation weight floor 0 -> 0.25 at lambda=0.15. Original-reference comparisons also enable the four V12 switches and are composite comparisons. Seed 20240933 was used to develop the hypothesis; independent validation remains required.

| pair | validation | accuracy | final ASR | attack mean ASR | normal exclusion |
|---|---|---:|---:|---:|---:|
| local_none_original_reference_s20240933 | validated | 52.79% → 52.38% | 10.60% → 15.69% | n/a → n/a | 25.83% → 8.00% |
| local_none_floor_ablation_s20240933 | validated | 45.74% → 52.38% | 19.07% → 15.69% | n/a → n/a | 46.33% → 8.00% |
| local_backdoor_original_reference_s20240933 | validated | 49.89% → 52.50% | 14.07% → 15.97% | 19.93% → 14.42% | 28.77% → 0.18% |
| local_backdoor_floor_ablation_s20240933 | validated | 49.61% → 52.50% | 18.21% → 15.97% | 17.14% → 14.42% | 25.61% → 0.18% |
| local_delayed_backdoor_original_reference_s20240933 | validated | 50.59% → 52.34% | 14.30% → 15.91% | 15.13% → 11.44% | 30.18% → 0.18% |
| local_delayed_backdoor_floor_ablation_s20240933 | validated | 51.49% → 52.34% | 14.72% → 15.91% | 14.76% → 11.44% | 21.05% → 0.18% |
| remote_none_original_reference_s20240935 | validated | 56.80% → 57.00% | 6.12% → 5.47% | n/a → n/a | 13.00% → 1.17% |
| remote_none_floor_ablation_s20240935 | validated | 57.15% → 57.00% | 6.30% → 5.47% | n/a → n/a | 10.00% → 1.17% |
| remote_backdoor_original_reference_s20240935 | validated | 57.50% → 55.71% | 7.72% → 5.06% | 15.39% → 6.42% | 20.18% → 0.00% |
| remote_backdoor_floor_ablation_s20240935 | validated | 56.67% → 55.71% | 5.02% → 5.06% | 6.29% → 6.42% | 11.58% → 0.00% |
| remote_delayed_backdoor_original_reference_s20240935 | validated | 55.13% → 56.18% | 11.76% → 5.03% | 10.02% → 5.74% | 14.91% → 0.00% |
| remote_delayed_backdoor_floor_ablation_s20240935 | validated | 57.18% → 56.18% | 6.23% → 5.03% | 6.07% → 5.74% | 12.98% → 0.00% |
