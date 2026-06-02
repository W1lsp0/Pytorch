"""Unit tests for server.sensitivity — calculate_layer_sensitivities."""

import math
import numpy as np
import pytest

from server.sensitivity import calculate_layer_sensitivities


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_client_data(weights: list, trust_score: float = 1.0) -> dict:
    return {"weights": weights, "trust_score": trust_score}


# ── edge cases ──────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_empty_layers_returns_empty(self):
        result = calculate_layer_sensitivities({}, [])
        assert result == []

    def test_single_layer_single_client(self):
        layer = np.array([1.0, 2.0, 3.0])
        client_map = {"c1": _make_client_data([layer.copy()], trust_score=0.9)}
        g_ref_layers = [layer.copy()]
        result = calculate_layer_sensitivities(client_map, g_ref_layers)
        assert len(result) == 1
        assert set(result[0].keys()) == {
            "s_privacy", "s_utility", "s_security",
            "s_total", "inclusion_threshold", "clip_target",
        }


# ── privacy sensitivity (static topology) ──────────────────────────────────

class TestPrivacy:
    def test_shallow_layer_higher_than_deep(self):
        """Shallow layers should have higher privacy sensitivity (exp decay)."""
        layers = [np.ones(10) for _ in range(5)]
        client_map = {"c1": _make_client_data([l.copy() for l in layers], 1.0)}
        result = calculate_layer_sensitivities(client_map, layers)

        # Layer 0 (shallowest) → exp(0) = 1.0
        # Layer 4 (deepest) → exp(-3 * 4/5) = exp(-2.4) ≈ 0.09
        assert result[0]["s_privacy"] > result[-1]["s_privacy"]

    def test_first_layer_privacy_is_one(self):
        """Layer index 0 → exp(-τ * 0/L) = exp(0) = 1.0."""
        layers = [np.ones(5) for _ in range(3)]
        client_map = {"c1": _make_client_data([l.copy() for l in layers], 1.0)}
        result = calculate_layer_sensitivities(client_map, layers)
        assert result[0]["s_privacy"] == pytest.approx(1.0, abs=0.001)


# ── utility sensitivity (gradient norm) ─────────────────────────────────────

class TestUtility:
    def test_layer_with_largest_norm_has_utility_one(self):
        """The layer whose reference gradient has the largest norm should get s_utility = 1.0."""
        layers = [
            np.array([1.0, 0.0]),   # norm = 1
            np.array([3.0, 4.0]),   # norm = 5 (max)
            np.array([0.0, 2.0]),   # norm = 2
        ]
        client_map = {"c1": _make_client_data([l.copy() for l in layers], 1.0)}
        result = calculate_layer_sensitivities(client_map, layers)
        assert result[1]["s_utility"] == pytest.approx(1.0, abs=0.001)

    def test_utility_proportional_to_norm(self):
        layers = [
            np.array([0.0, 0.0, 1.0]),   # norm = 1
            np.array([0.0, 0.0, 2.0]),   # norm = 2
        ]
        client_map = {"c1": _make_client_data([l.copy() for l in layers], 1.0)}
        result = calculate_layer_sensitivities(client_map, layers)
        # s_utility[0] = 1/2, s_utility[1] = 2/2
        assert result[0]["s_utility"] == pytest.approx(0.5, abs=0.01)
        assert result[1]["s_utility"] == pytest.approx(1.0, abs=0.01)


# ── security sensitivity (adversarial divergence) ───────────────────────────

class TestSecurity:
    def test_fully_aligned_clients_low_security_risk(self):
        """When all clients align perfectly with the reference, s_security ≈ 0."""
        layer = np.array([1.0, 2.0])
        client_map = {
            "c1": _make_client_data([layer.copy()], 1.0),
            "c2": _make_client_data([layer.copy()], 1.0),
        }
        result = calculate_layer_sensitivities(client_map, [layer.copy()])
        # cos_sim = 1.0, weighted avg = 1.0 → s_security = 0.0
        assert result[0]["s_security"] == pytest.approx(0.0, abs=0.01)

    def test_opposing_client_higher_security_risk(self):
        """A client opposing the reference raises s_security."""
        ref = np.array([1.0, 0.0])
        bad = np.array([-1.0, 0.0])
        client_map = {
            "good": _make_client_data([ref.copy()], 1.0),
            "bad":  _make_client_data([bad.copy()], 1.0),
        }
        result = calculate_layer_sensitivities(client_map, [ref.copy()])
        # weighted cos = (1*1 + 1*(-1)) / 2 = 0 → s_security = 1 - 0 = 1.0
        assert result[0]["s_security"] == pytest.approx(1.0, abs=0.01)


# ── inclusion threshold & clip target ───────────────────────────────────────

class TestGateParameters:
    def test_higher_sensitivity_raises_threshold(self):
        """Layers with higher s_total should have higher inclusion_threshold."""
        # Create two layers: one high sensitivity, one low
        big_layer = np.array([10.0, 0.0])
        small_layer = np.array([1.0, 0.0])
        ref_layers = [big_layer.copy(), small_layer.copy()]
        client_map = {
            "c1": _make_client_data(
                [big_layer.copy(), small_layer.copy()], 1.0
            ),
        }
        result = calculate_layer_sensitivities(client_map, ref_layers)
        # Layer 0 has higher utility → higher s_total → higher threshold
        assert result[0]["inclusion_threshold"] >= result[1]["inclusion_threshold"]

    def test_higher_sensitivity_lowers_clip(self):
        """Layers with higher s_total should have lower clip_target (stricter clipping)."""
        big_layer = np.array([10.0, 0.0])
        small_layer = np.array([1.0, 0.0])
        ref_layers = [big_layer.copy(), small_layer.copy()]
        client_map = {
            "c1": _make_client_data(
                [big_layer.copy(), small_layer.copy()], 1.0
            ),
        }
        result = calculate_layer_sensitivities(client_map, ref_layers)
        assert result[0]["clip_target"] <= result[1]["clip_target"]

    def test_all_values_positive(self):
        """All computed values should be positive."""
        layers = [np.random.default_rng(0).standard_normal(20) for _ in range(4)]
        client_map = {
            f"c{i}": _make_client_data([l.copy() for l in layers], 0.8)
            for i in range(3)
        }
        result = calculate_layer_sensitivities(client_map, [l.copy() for l in layers])
        for entry in result:
            assert entry["inclusion_threshold"] > 0
            assert entry["clip_target"] > 0


# ── s_total fusion ──────────────────────────────────────────────────────────

class TestFusion:
    def test_s_total_is_weighted_sum(self):
        """s_total should equal 0.3*privacy + 0.4*utility + 0.3*security."""
        layer = np.array([1.0, 0.0])
        client_map = {"c1": _make_client_data([layer.copy()], 1.0)}
        result = calculate_layer_sensitivities(client_map, [layer.copy()])
        r = result[0]
        expected = 0.3 * r["s_privacy"] + 0.4 * r["s_utility"] + 0.3 * r["s_security"]
        assert r["s_total"] == pytest.approx(expected, abs=0.01)
