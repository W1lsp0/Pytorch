# V13 layer gate paired audit

V13 changes only the layer gate lambda from 0.15 to 0.05, with all V12 probation/low-entropy switches held on. Same-host seed pairs are required; this is a layer-gate ablation, not a final security claim.

| pair | validation | accuracy | final ASR | attack mean ASR | normal exclusion |
|---|---|---:|---:|---:|---:|
| local_none_s20240934 | validated | 53.64% → 55.45% | 4.14% → 4.49% | n/a → n/a | 12.00% → 6.17% |
| local_backdoor_s20240934 | validated | 54.80% → 54.55% | 3.84% → 4.37% | 7.43% → 6.81% | 13.33% → 8.77% |
| local_delayed_backdoor_s20240934 | validated | 54.03% → 55.44% | 4.09% → 4.71% | 7.35% → 7.22% | 9.47% → 6.32% |
| remote_none_s20240935 | validated | 56.69% → 56.46% | 5.44% → 5.70% | n/a → n/a | 8.67% → 7.17% |
| remote_backdoor_s20240935 | validated | 56.92% → 56.28% | 5.70% → 4.59% | 6.61% → 6.36% | 9.82% → 9.82% |
| remote_delayed_backdoor_s20240935 | validated | 56.57% → 56.78% | 5.77% → 5.72% | 6.81% → 6.54% | 8.77% → 7.72% |
