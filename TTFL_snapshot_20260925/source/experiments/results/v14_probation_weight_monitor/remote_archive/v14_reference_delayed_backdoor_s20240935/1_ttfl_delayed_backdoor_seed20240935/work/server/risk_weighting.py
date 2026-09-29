"""Risk attenuation with an optional bounded weight during soft probation."""
import math


def risk_weight_factor(risk, power, probation=False, floor=0.0):
    if not math.isfinite(floor) or not 0 <= floor <= 1:
        raise ValueError('RISK_PROBATION_WEIGHT_FLOOR must be finite and in [0, 1]')
    factor = max(0.0, 1.0 - risk) ** power
    # Eligibility and hard isolation are decided separately by the strategy.
    return max(factor, floor) if probation else factor
