"""Executable control core for revision 7; no training, database or TEE claims.

The server supplies gradient/proxy measurements and an ordered trainable tensor
manifest. The validation fixtures deliberately inject constructed evidence.
"""
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from statistics import median

import numpy as np

CFG = json.loads(Path(__file__).with_name("config.json").read_text())
EPS = CFG["norm_epsilon"]


def clip(x):
    return float(np.clip(x, 0.0, 1.0))


def cosine(x, y):
    x, y = np.asarray(x).ravel(), np.asarray(y).ravel()
    nx, ny = float(np.linalg.norm(x)), float(np.linalg.norm(y))
    if nx <= EPS or ny <= EPS:
        return None
    return float(np.clip(np.dot(x, y) / (nx * ny), -1.0, 1.0))


def calibrate(nonnegative_values):
    """Server-calibration statistic; never infers a scale from final test results."""
    raw = [float(x) for x in nonnegative_values]
    if not raw or not all(math.isfinite(x) for x in raw):
        raise ValueError("Finite calibration observations are required")
    values = [max(0.0, x) for x in raw]
    m = median(values)
    mad = median(abs(x-m) for x in values)
    return max(CFG["calibration_floor"], m+CFG["calibration_mad_multiplier"]*mad)


def activation_kl(base, candidate):
    """Mean sample KL after softmax over flattened features, never over batch."""
    a, b = np.asarray(base, dtype=float), np.asarray(candidate, dtype=float)
    if a.shape != b.shape or a.ndim < 2 or a.shape[0] == 0:
        raise ValueError("Matching nonempty [batch, features, ...] tensors required")
    if not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("Nonfinite activations")
    def logsoftmax(x):
        x = x.reshape(x.shape[0], -1)
        x = x-x.max(axis=1, keepdims=True)
        return x-np.log(np.exp(x).sum(axis=1, keepdims=True))
    la, lb = logsoftmax(a), logsoftmax(b)
    return max(0.0, float(np.mean(np.sum(np.exp(la)*(la-lb), axis=1))))


@dataclass
class State:
    status: str = "NORMAL"
    alpha: float = CFG["history_alpha0"]
    beta: float = CFG["history_beta0"]
    risk: float = CFG["risk0"]
    trust: float = CFG["trust0"]
    covariance: float = CFG["covariance0"]
    n: int = 0
    bad: int = 0
    good: int = 0
    hard: int = 0

    @property
    def history(self):
        return self.alpha/(self.alpha+self.beta)


def ceiling(n):
    """Attainable best-evidence envelope after n complete nonzero submissions."""
    p, a, b = CFG["covariance0"], CFG["history_alpha0"], CFG["history_beta0"]
    for _ in range(n):
        pm = p+CFG["process_noise"]
        p = pm/(1.0+pm)
        a = CFG["history_decay"]*a+1.0
        b = CFG["history_decay"]*b
    return (1.0/(1.0+p))**CFG["trust_power"]*(a/(a+b))**CFG["history_power"]


def threshold(sensitivity):
    if not math.isfinite(sensitivity) or not 0 <= sensitivity <= 1:
        raise ValueError("Sensitivity must be in [0, 1]")
    z = CFG["gate_sensitivity"]*sensitivity
    return CFG["gate_base"]+(1-CFG["gate_base"])*z/(1+z)


def advance(state, quality=None, instant=None, entropy=0.0, valid=True, nonzero=True):
    before = asdict(state)
    event = dict(start_state=state.status, quality=quality, instant_risk=instant,
                 history_before=state.history, risk_before=state.risk,
                 bad_before=state.bad, good_before=state.good, hard_before=state.hard)
    if state.status == "BLACKLIST":
        reason = "blacklist_gate"
    elif not valid or quality is None or instant is None:
        reason = "missing_audit"
    elif not nonzero:
        reason = "no_operation"
    else:
        if not all(math.isfinite(x) and 0 <= x <= 1 for x in (quality, instant, entropy)):
            raise ValueError("Audit observations must be finite and bounded")
        pm = state.covariance+CFG["process_noise"]
        gain = pm/(pm+math.exp(CFG["entropy_scale"]*entropy))
        observation = CFG["runtime_weight"]+(1-CFG["runtime_weight"])*(1-entropy)
        state.trust += gain*(observation-state.trust)
        state.covariance = (1-gain)*pm
        state.alpha = CFG["history_decay"]*state.alpha+quality
        state.beta = CFG["history_decay"]*state.beta+1-quality
        state.risk = CFG["risk_decay"]*state.risk+(1-CFG["risk_decay"])*instant
        state.n += 1
        bad = state.history < CFG["history_floor"] or state.risk >= CFG["review_risk"]
        state.bad = state.bad+1 if bad else 0
        state.good = state.good+1 if not bad else 0
        state.hard = state.hard+1 if state.status == "QUARANTINE" and state.risk >= CFG["blacklist_risk"] else 0
        reason = "hold"
        if state.status == "NORMAL" and state.bad >= CFG["review_patience"]:
            state.status, reason = "SUSPECT", "persistent_low_history_or_risk"
        elif state.status == "SUSPECT":
            if state.bad >= CFG["quarantine_patience"] or instant >= CFG["instant_quarantine"]:
                state.status, reason = "QUARANTINE", "persistent_bad_or_instant_risk"
            elif state.good >= CFG["recovery_patience"]:
                state.status, reason = "NORMAL", "recovery"
        elif state.status == "QUARANTINE":
            if state.hard >= CFG["blacklist_patience"]:
                state.status, reason = "BLACKLIST", "persistent_high_risk"
            elif state.good >= CFG["recovery_patience"]:
                state.status, reason = "SUSPECT", "recovery"
        if state.status != before["status"]:
            trigger_counts = (state.bad, state.good, state.hard)
            state.bad = state.good = state.hard = 0
        else:
            trigger_counts = (state.bad, state.good, state.hard)
        event.update(trigger_bad=trigger_counts[0], trigger_good=trigger_counts[1], trigger_hard=trigger_counts[2])
    advanced = state.n != before["n"]
    raw = ((state.trust/(1+state.covariance))**CFG["trust_power"]
           * quality**CFG["content_power"]*state.history**CFG["history_power"]
           * (1-state.risk)**CFG["risk_power"]) if advanced else 0.0
    event.update(end_state=state.status, history=state.history, risk_ema=state.risk,
                 bad_after=state.bad, good_after=state.good, hard_after=state.hard,
                 reason=reason, raw_score=raw, gate_score=raw/ceiling(state.n) if advanced else 0.0,
                 eligible=advanced and state.status in ("NORMAL", "SUSPECT"), complete_submissions=state.n)
    return event


def audit(delta, root, peers, loss_increase, activation_drift, loss_scale, activation_scale,
          proxy_available=True, admitted=True):
    """peers: (delta, trust_score) pairs, already frozen and excluding self."""
    delta, root = np.asarray(delta, dtype=float).ravel(), np.asarray(root, dtype=float).ravel()
    if delta.shape != root.shape or not np.isfinite(delta).all() or not np.isfinite(root).all():
        raise ValueError("Finite matching updates and root required")
    nonzero = np.linalg.norm(delta) > EPS
    if not proxy_available or not admitted:
        return dict(quality=None, instant=None, valid=False, nonzero=bool(nonzero), channels={})
    if not all(math.isfinite(x) and x > 0 for x in (loss_scale, activation_scale)):
        raise ValueError("Positive calibration scales required")
    if not all(math.isfinite(x) for x in (loss_increase, activation_drift)):
        raise ValueError("Finite proxy measurements required")
    channels = dict(loss=clip(max(0.0, loss_increase)/loss_scale), activation=clip(activation_drift/activation_scale))
    c = cosine(delta, root)
    quality = CFG["contribution_offset"]+CFG["contribution_scale"]*c if c is not None else (1-channels["loss"])*(1-channels["activation"])
    if c is not None:
        channels["direction"] = (1-c)/2
    usable = []
    for other, trust in peers:
        if not math.isfinite(trust) or trust < 0:
            raise ValueError("Invalid peer trust")
        cp = cosine(delta, other)
        if cp is not None and trust > 0:
            usable.append((cp, trust, float(np.linalg.norm(other))))
    if usable:
        mass = sum(w for _, w, _ in usable)
        cpeer = sum(c*w for c,w,_ in usable)/mass
        consistency = CFG["contribution_offset"]+CFG["contribution_scale"]*cpeer
        b2 = CFG["fusion_beta"]**2
        quality = (1+b2)*quality*consistency/(b2*consistency+quality)
        channels["peer"] = clip(1-cpeer)
        scale = median(norm for _,_,norm in usable)
    else:
        scale = float(np.linalg.norm(root))
    if nonzero and scale > EPS:
        channels["amplitude"] = clip(float(np.linalg.norm(delta))/scale-1)
    return dict(quality=clip(quality), instant=max(channels.values()), valid=True,
                nonzero=bool(nonzero), channels=channels)


def aggregate(updates, events, sample_counts, reference_ids, root_blocks, block_names):
    """Aggregate named trainable blocks; return applied increments and full audit.

    reference_ids are the frozen pre-round R_t. T_t=R_t intersect A_t, so newly
    recovered clients do not shape the same-round thresholds or clipping radii.
    Empty T_t uses server root magnitudes and direction-only layer statistics.
    """
    if len(root_blocks) != len(block_names) or not block_names or len(set(block_names)) != len(block_names):
        raise ValueError("One unique name required per trainable block")
    for cid, blocks in updates.items():
        if len(blocks) != len(root_blocks) or sample_counts[cid] <= 0 or not math.isfinite(sample_counts[cid]):
            raise ValueError("Invalid block count or sample count")
        if any(np.shape(x) != np.shape(r) or not np.isfinite(x).all() for x,r in zip(blocks,root_blocks)):
            raise ValueError("Invalid block shape or values")
    active = [cid for cid in updates if events[cid]["eligible"]]
    stats_ids = [cid for cid in active if cid in reference_ids]
    roots = [float(np.linalg.norm(x)) for x in root_blocks]
    maxroot = max(roots)
    applied, rows, layer_rows = [], [], []
    for l, (name, root) in enumerate(zip(block_names, root_blocks)):
        cs = [cosine(updates[cid][l], root) for cid in stats_ids]
        cs = [c for c in cs if c is not None]
        depth = math.exp(-CFG["depth_decay"]*(l+1)/len(block_names))
        utility = roots[l]/maxroot if maxroot > EPS else 0.0
        security = (1-sum(cs)/len(cs))/2 if cs else 0.0
        wp,wu,ws = CFG["sensitivity_weights"]
        sensitivity = wp*depth+wu*(1-utility)+ws*security
        gate = threshold(sensitivity)
        norms = [float(np.linalg.norm(updates[cid][l])) for cid in stats_ids]
        base = median(norms) if norms else roots[l]
        radius = base/(1+sensitivity)
        survivors = [cid for cid in active if events[cid]["gate_score"] >= gate
                     and events[cid]["raw_score"] > 0 and np.linalg.norm(updates[cid][l]) > EPS] if radius > EPS else []
        mass = sum(sample_counts[cid]*events[cid]["raw_score"] for cid in survivors)
        total = np.zeros_like(root, dtype=float)
        for cid, blocks in updates.items():
            before = float(np.linalg.norm(blocks[l]))
            weight = sample_counts[cid]*events[cid]["raw_score"]/mass if cid in survivors else 0.0
            clipped = np.asarray(blocks[l], dtype=float)*min(1.0, radius/before) if weight > 0 else np.zeros_like(root, dtype=float)
            increment = weight*clipped
            total += increment
            rows.append(dict(client_id=cid, block=name, trainable=True, state=events[cid]["end_state"],
                             raw_score=events[cid]["raw_score"], gate_score=events[cid]["gate_score"],
                             threshold=gate, passed=cid in survivors, normalized_weight=weight,
                             norm_before=before, norm_after=float(np.linalg.norm(clipped)),
                             applied_norm=float(np.linalg.norm(increment)), stats_member=cid in stats_ids))
        applied.append(total)
        layer_rows.append(dict(block=name, sensitivity=sensitivity, threshold=gate, radius=radius,
                               stats_count=len(stats_ids), survivors=len(survivors),
                               skipped=not survivors, applied_norm=float(np.linalg.norm(total))))
    return applied, rows, layer_rows
