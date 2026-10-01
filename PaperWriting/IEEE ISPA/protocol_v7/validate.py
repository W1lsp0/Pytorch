"""Deterministic protocol tests, not CIFAR-10 or hardware measurements.

Run: python protocol_v7/validate.py
Artifacts include exact event/weight traces and source hashes.
"""
import csv
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from controller import CFG, State, activation_kl, advance, aggregate, audit, calibrate, ceiling, cosine, threshold

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"
OUT.mkdir(exist_ok=True)
results, traces, block_traces, layer_traces = [], [], [], []


def check(name, fn):
    details = fn()
    results.append(dict(test=name, passed=True, details=details))


def log_event(case, round_id, cid, event):
    traces.append(dict(case=case, round=round_id, client_id=cid, **event))


def legacy_counterexample():
    status, bad, history, risk = "NORMAL", 0, .5, 0.0
    rows = []
    for t in range(1, 41):
        if status != "QUARANTINE":
            # Independent closed form for the manuscript's unit-evidence Beta.
            d = .9**t
            mass = (1-d)/.1
            history = (d+.8*mass)/(2*d+mass)
            risk = .3*(1-.85**t)
            bad = bad+1 if history < .74 or risk >= .64 else 0
            limit = 2 if status == "NORMAL" else 3
            if bad >= limit:
                status = "SUSPECT" if status == "NORMAL" else "QUARANTINE"
                bad = 0
        rows.append(dict(round=t, history=history, risk=risk, state=status,
                         peer_set_empty=status == "QUARANTINE"))
    assert rows[1]["state"] == "SUSPECT" and rows[4]["state"] == "QUARANTINE"
    assert all(x["history"] == rows[4]["history"] for x in rows[5:])
    save_csv("legacy_deadlock.csv", rows)
    return dict(suspect_round=2, quarantine_round=5, frozen_rounds="6--40", history_at_freeze=history)


def healthy_startup():
    s = State()
    for t in range(1, 41):
        e = advance(s, .8, .3)
        log_event("healthy_startup", t, 0, e)
        assert s.status == "NORMAL"
        d, mass = .9**t, (1-.9**t)/.1
        assert math.isclose(s.history, (d+.8*mass)/(2*d+mass), abs_tol=1e-12)
        assert math.isclose(s.risk, .3*(1-.85**t), abs_tol=1e-12)
    return dict(rounds=40, review_events=0, quarantine_events=0)


def collective_recovery():
    states = {k: State(status="QUARANTINE", risk=.95) for k in range(20)}
    first_selected, first_normal = None, None
    root = np.array([1., 0.])
    for t in range(1, 11):
        refs = {k for k,s in states.items() if s.status in ("NORMAL", "SUSPECT") and s.risk < .64}
        updates = {k:[root.copy()] for k in states}
        trust_before = {k:s.trust/(1+s.covariance) for k,s in states.items()}
        events = {}
        for k,s in states.items():
            peers = [(root.copy(), trust_before[j]) for j in refs if j != k]
            ev = audit(root, root, peers, 0, 0, 1, 1)
            e = advance(s, **{a:b for a,b in ev.items() if a != "channels"})
            log_event("collective_recovery", t, k, e)
            events[k] = e
        applied, rows, layers = aggregate(updates, events, {k:1 for k in states}, refs, [root], ["toy.weight"])
        for row in rows:
            block_traces.append(dict(case="collective_recovery", round=t, **row))
        for row in layers:
            layer_traces.append(dict(case="collective_recovery", round=t, **row))
        if t <= 3:
            assert not refs and np.array_equal(applied[0], np.zeros(2))
        if any(np.linalg.norm(x) > 0 for x in applied) and first_selected is None:
            first_selected = t
            assert not refs  # recovery succeeds without rebuilding peers first
            assert all(row["normalized_weight"] > 0 for row in rows)
            assert all(not row["stats_member"] for row in rows)
        if all(s.status == "NORMAL" for s in states.values()) and first_normal is None:
            first_normal = t
    assert (first_selected, first_normal) == (4, 6)
    return dict(clients=20, initial_risk=.95, first_nonzero_applied_round=first_selected, all_normal_round=first_normal)


def maximal_risk():
    s, first = State(), {}
    for t in range(1, 21):
        e = advance(s, 1., 1.)
        log_event("maximal_risk", t, 0, e)
        if s.status not in first:
            first[s.status] = t
        if t <= 18:
            assert math.isclose(s.risk, 1-.85**t, abs_tol=1e-12)
        if t == 19:
            assert e["reason"] == "blacklist_gate"
    assert first["SUSPECT"] == 8 and first["QUARANTINE"] == 9 and first["BLACKLIST"] == 18
    return dict(**first, first_blacklist_gate=19)


def score_envelope():
    s = State()
    smallest_margin = 1.0
    for n in range(1, 101):
        e = advance(s, 1., 0., entropy=0.)
        assert math.isclose(e["raw_score"], ceiling(n), rel_tol=1e-12)
        assert math.isclose(e["gate_score"], 1.0, rel_tol=1e-12)
        for sens in np.linspace(0, 1, 101):
            smallest_margin = min(smallest_margin, e["gate_score"]-threshold(float(sens)))
            assert e["gate_score"] >= threshold(float(sens))
    pstar = (math.sqrt(.01**2+4*.01)-.01)/2
    legacy_first = (1+.26/1.26)**-3*math.sqrt(1.9/2.8)
    smax = (legacy_first-.4)/1.2
    depth = -math.log(smax/.3)/3
    return dict(legacy_first_cap=legacy_first, legacy_forbidden_depth_fraction=depth,
                legacy_asymptotic_cap=(1+pstar)**-3,
                new_max_gate=threshold(1.), minimum_ideal_margin=smallest_margin,
                checks=100*101)


def empty_gate():
    e = advance(State(), .1, .2)
    q = dict(e, eligible=False, end_state="QUARANTINE", gate_score=1., raw_score=1.)
    old = np.array([7., -2.])
    increment, rows, _ = aggregate({0:[np.ones(2)], 1:[np.ones(2)]}, {0:e,1:q},
                                    {0:1,1:1000}, {0}, [np.ones(2)], ["toy.weight"])
    assert np.array_equal(old+increment[0], old)
    assert all(r["normalized_weight"] == 0 for r in rows)
    return dict(survivors=0, quarantined_high_score_backfilled=False, model_unchanged=True)


def missing_evidence():
    s = State(status="QUARANTINE", risk=.8, good=1)
    before = asdict(s)
    e = advance(s, valid=False)
    assert asdict(s) == before and not e["eligible"]
    root = np.array([1., 0.])
    a = audit(root, root, [], 0., 0., 1., 1.)
    assert a["valid"] and "peer" not in a["channels"] and a["quality"] == 1.
    solo = advance(State(), **{k:v for k,v in a.items() if k != "channels"})
    delta, rows, _ = aggregate({0:[root]}, {0:solo}, {0:5}, {0}, [root], ["toy.weight"])
    assert rows[0]["normalized_weight"] == 1. and np.linalg.norm(delta[0]) > 0
    return dict(missing_proxy_freezes=True, missing_peer_audit_valid=True, sole_client_weight=1.)


def zero_and_small_updates():
    for norm in (0., 1e-15, 1e-12):
        s = State()
        before = asdict(s)
        a = audit(np.array([norm, 0.]), np.array([1.,0.]), [], 0.,0.,1.,1.)
        assert "direction" not in a["channels"]
        e = advance(s, **{k:v for k,v in a.items() if k != "channels"})
        assert e["reason"] == "no_operation" and asdict(s) == before
    assert cosine(np.zeros(2), np.ones(2)) is None
    return dict(norms=[0.,1e-15,1e-12], false_direction_risk=False, history_increase=False)


def sample_weights_and_clipping():
    e0, e1 = advance(State(),1.,0.), advance(State(),1.,0.)
    delta, rows, layers = aggregate({0:[np.array([10.,0.])], 1:[np.array([10.,0.])]},
                                   {0:e0,1:e1}, {0:1,1:3}, {0,1}, [np.array([10.,0.])], ["toy.weight"])
    assert [r["normalized_weight"] for r in rows] == [.25,.75]
    radius = layers[0]["radius"]
    assert np.linalg.norm(delta[0]) <= radius+1e-12
    assert all(r["norm_after"] <= radius+1e-12 for r in rows)
    assert math.isclose(sum(r["applied_norm"] for r in rows), np.linalg.norm(delta[0]))
    for row in rows:
        block_traces.append(dict(case="sample_weights", round=1, **row))
    return dict(weights=[.25,.75], clip_radius=radius, applied_norm=float(np.linalg.norm(delta[0])))


def positive_calibration_and_activation_axis():
    assert calibrate([0,0,0]) == 1e-6
    assert calibrate([.1,.2,.3]) > 0
    for invalid in ([float("nan")], [float("inf")], []):
        try:
            calibrate(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid calibration observations accepted")
    a = np.array([[1.,2.,4.],[9.,2.,1.]])
    b = np.array([[2.,2.,3.],[5.,3.,0.]])
    both = activation_kl(a,b)
    individual = (activation_kl(a[:1],b[:1])+activation_kl(a[1:],b[1:]))/2
    assert math.isclose(both,individual,abs_tol=1e-12)
    assert activation_kl(a,a) == 0
    return dict(calibration_floor=1e-6, kl_sample_axis_verified=True)


def bounded_random_evidence():
    rng = np.random.default_rng(20261001)
    for _ in range(100):
        s = State()
        for _ in range(100):
            e = advance(s,*map(float,rng.random(2)), entropy=float(rng.random()))
            assert 0 <= s.history <= 1 and 0 <= s.risk <= 1
            assert 0 <= e["gate_score"] <= 1+1e-12
            assert not e["eligible"] if s.status in ("QUARANTINE","BLACKLIST") else True
    return dict(seed=20261001, sequences=100, steps_per_sequence=100)


def save_csv(name, rows):
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with (OUT/name).open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


for name, fn in [
    ("legacy_deadlock_reproduced", legacy_counterexample),
    ("healthy_startup", healthy_startup),
    ("collective_quarantine_recovery", collective_recovery),
    ("pure_ema_blacklist_timing", maximal_risk),
    ("attainable_gate_envelope", score_envelope),
    ("empty_gate_no_backfill", empty_gate),
    ("missing_proxy_and_single_client", missing_evidence),
    ("zero_and_near_zero_updates", zero_and_small_updates),
    ("sample_weights_and_clipping", sample_weights_and_clipping),
    ("calibration_and_activation_axis", positive_calibration_and_activation_axis),
    ("bounded_random_evidence", bounded_random_evidence),
]:
    check(name,fn)

save_csv("state_events.csv", traces)
save_csv("block_events.csv", block_traces)
save_csv("layer_events.csv", layer_traces)
summary = dict(evidence_type="Constructed control tests; not training or hardware measurements",
               tests=results, passed=len(results),
               source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in (HERE/"controller.py", HERE/"config.json", Path(__file__))})
(OUT/"validation.json").write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps(summary,indent=2))
