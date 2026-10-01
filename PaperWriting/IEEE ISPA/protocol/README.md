# TTFL controller

This directory is an executable controller specification and a deterministic
verification bundle. It does **not** reproduce historical CIFAR-10 training or
hardware measurements. `config.json` fixes the new design choices; no result is
used to tune them against a final classification test set.

From the parent ISPA directory:

```bash
python protocol/validate.py
python protocol/audit_old_trace.py
python protocol/plot_validation.py
```

The controller requires NumPy; plotting additionally requires Matplotlib.
No application imports, database access, training, or telemetry collection occur.

Inputs to `audit` are the submitted trainable update, server reference increment,
frozen peer updates and positive trust weights, measured loss increase and
sample-wise activation KL, and positive calibration scales. The outer adapter
must bind those measurements to the same model/update/proxy indices. Invalid
admission or a missing server audit freezes state and excludes the update.
Missing peers are optional; zero/near-zero complete updates are no-operations.

At round start, freeze the peer identities and their trust weights. `advance`
updates each client's scalar filter and unit-evidence history/risk exactly once;
its event reports the transition counters before reset. `aggregate` consumes
those events and the frozen identities, forms the post-transition candidates,
and computes numerical weights and increments per named trainable tensor.
Nontrainable buffers are outside its API. A complete training adapter is not
included and must not mistake a state dictionary's buffers for these blocks.

`results/validation.json` records the eleven test groups and hashes of the
controller, configuration and validation script. The fixtures have no measured
accuracy or attack success rate. `state_events.csv`, `block_events.csv`, and
`layer_events.csv` are executed synthetic traces; `threshold_peer_counterexample.csv` evaluates a deliberately wrong utility
cutoff of 0.74 combined with mandatory peers; it is not a reconstruction of a
training run or evidence that the original implementation used that cutoff.

`legacy_observed_events.csv` is different: it joins the *existing local logs*
and keeps unrecorded instantaneous risk, full state and applied-update fields
empty. Displayed state is not asserted to be a complete state-machine truth.
The local snapshot's risk override and blacklist branches differ from this controller.

The collective-recovery test also executes a matched peer-required arm with
identical initial states, update/reference vectors, proxy observations, and
controller parameters. Only audit admission additionally requires usable peers.
This arm remains quarantined with zero updates through ten attempted audits;
its events are labeled `peer_required_recovery` in the same CSV files. This is
a constructed policy comparison, not a rerun of the partial training code.

The figure `../figures/collective_recovery.pdf` uses only the server-supported recovery trace.
All 20 clients have identical inputs in that fixture; the plotted state and risk
are their common trajectory, not an average with omitted variability. The
bottom panel is the actual aggregate increment norm of a two-dimensional toy
block. Its arbitrary units must not be relabeled as model performance.

For this project, new non-data logic diagrams use the imagegen skill as requested
by the author. Quantitative figures use reproducible plotting tools and recorded
data. Measured plot values remain unchanged; presentation-only changes are documented
in the parent `DATA_PROVENANCE.md`.
