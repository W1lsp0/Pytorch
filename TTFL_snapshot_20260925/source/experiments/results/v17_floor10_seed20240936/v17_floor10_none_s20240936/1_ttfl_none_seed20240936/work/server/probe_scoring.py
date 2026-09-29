"""Alternative known-trigger score; no threshold or state-machine changes."""
import math


def calibrate_trigger_scores(raw_br, raw_tl, clean_score, mode):
    if mode not in ('legacy', 'clean_delta'):
        raise ValueError(f'unknown trigger score mode: {mode}')
    required = [raw_br, raw_tl] + ([clean_score] if mode == 'clean_delta' else [])
    if any(v is None or not math.isfinite(v) or not 0 <= v <= 1 for v in required):
        raise ValueError('probe scores must be finite probabilities in [0, 1]')
    if mode == 'legacy':
        return raw_br, raw_tl
    return max(0.0, raw_br-clean_score), max(0.0, raw_tl-clean_score)
