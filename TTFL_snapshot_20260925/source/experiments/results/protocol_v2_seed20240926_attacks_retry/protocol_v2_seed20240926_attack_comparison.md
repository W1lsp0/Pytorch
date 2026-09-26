# Protocol v2 second-seed attack comparison

Dataset: local CIFAR-10; 20 clients; 4 rounds; 1 local epoch; malicious client C1; poison rate 1.0; server proxy 500; no shared client pool.

| Scenario | Method | Final clean accuracy | Final backdoor ASR | Round-4 normal exclusion | Fit audit |
|---|---|---:|---:|---:|---|
| backdoor | fedavg | 26.89% | 33.08% | n/a | 20/20, 0 failures x4 |
| backdoor | fltrust | 32.22% | 18.00% | n/a | 20/20, 0 failures x4 |
| backdoor | single_stream | 30.39% | 3.21% | 26.3% | 20/20, 0 failures x4 |
| backdoor | ttfl | 30.00% | 24.83% | 0.0% | 20/20, 0 failures x4 |
| delayed_backdoor | fedavg | 26.93% | 32.33% | n/a | 20/20, 0 failures x4 |
| delayed_backdoor | fltrust | 33.77% | 16.30% | n/a | 20/20, 0 failures x4 |
| delayed_backdoor | single_stream | 28.29% | 31.86% | 26.3% | 20/20, 0 failures x4 |
| delayed_backdoor | ttfl | 28.46% | 31.68% | 0.0% | 20/20, 0 failures x4 |
