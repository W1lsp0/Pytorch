# V13 dynamic scheduling handoff

V12 is complete: 8/8 supplementary runs finished, 6/6 strict same-host seed-20240933 pairs validated, 3 seed-20240932 historical pairs reported separately. `../v12_matched_monitor/closeout.json` is paired_reports_complete with goal_achieved=false. V12 does not achieve the objective: attack final ASR regresses in every strict seed-33 attack pair; local persistent-backdoor accuracy and honest exclusion also regress. Do not adopt it as a final method.

The old whole-batch waiter (PID 919777) and old V13 watcher (PID 924360) were explicitly stopped after verifying their command lines; no training process was stopped. Original V12 training snapshots remain untouched.

Dynamic node supervisors now allocate any free GPU on the SAME host from a common queue, using unique ports and immutable training sources. No cross-host comparisons. All five local / three remote GPUs are eligible. A full 20-client trial requires 21000 MiB free and a GPU without existing compute processes (utilization <=10%, used <=500MiB). Existing trial peaks approach 19GiB; placing another full trial in remaining memory on foreign jobs is unsafe. The scheduler reserves a slot before CUDA initialization, records launches, checks every30 seconds and reuses released slots. Foreign processes are never signaled. Queued jobs are not tied to a GPU. No automatic retry overwrites a failed run.

Current launch PIDs (verify liveness): local supervisor 961098, remote supervisor 32749, central watcher 964328. Local GPUs0/1/3/4 run none baseline/relaxed and backdoor baseline/relaxed; remote GPUs1/2 run none baseline/relaxed. Local GPU2 has a foreign job; remote GPU0 has a foreign vLLM process taking ~18.7GiB. Both automatically become eligible after release. Remaining six trials queue on their respective hosts.

Local training source frozen at `source/` in this monitor directory. Remote training source `/mnt/data/zjk/TTFL/v13_source`. Local result root `../v13_layer_gate_seed20240934`; remote result root `/mnt/data/zjk/TTFL/results/v13_layer_gate_seed20240935`. See local_plan.json and remote_plan.json (jobs, no longer fixed slots). No edits to training snapshots while jobs are active.

Fixed audit/monitor defects before starting:
- pairs.json now points to actual `1_ttfl_*` run directories, not enclosing matrices;
- duplicate-key report merge corrected;
- remote monitor includes `/results/` in its path;
- report validates all fixed risk thresholds, source, initialization, partitions, attack schedules and complete training/evaluation;
- central sync errors and stale heartbeats are surfaced, output is atomic;
- completion marker is emitted ONLY when all six pairs validate, never just because reporter exits0;
- baseline and relaxed use same host/source/seed and only lambda0.15 ->0.05 differs; both include prior probe/streak changes, so comparison to unmodified V12 is not a single-change comparison.

Tests: 12 admission/report/pairing regressions passed. Started local and remote manifests checked against lambda and frozen source. Six first-round fit aggregations reached20 clients/0 failures.

`decision.json` is a conservative zero-tolerance descriptive screen: require no accuracy regression, strictly lower honest exclusion and no attack final/mean/peak ASR regression across pairs. Passing only qualifies for further evaluation against original baseline and new seeds; goal_achieved remains false. Failing records regression metrics for the next mechanism revision, it does not invent a new algorithm automatically.

`health.json` + `health_events.jsonl`: persistent monitoring. `matched_report.json/md`: current pair audit. `decision.json`: development screen. `closeout.json`: validated completion only. `/data1/lab409/W1lsp0/EXPERIMENT_COMPLETE_REMINDER.json` is a durable handoff FILE; it does not wake the assistant or deliver a desktop notification. No callable automation connector was available.

Correction to earlier causal claim: V12 did NOT save raw_score/threshold arrays, so the earlier quoted typical score range0.04--0.08 was not measured from these audits. `v12_exclusion_paths.json` directly supports stage attribution: local seed33 backdoor normal total270, layer-gate without logged isolation221, aggregation isolation7, pre-layer blacklist42; none total134, layer-gate130, aggregation isolation4. This is evidence for testing the gate hypothesis, not proof of the outcome of changing lambda.
