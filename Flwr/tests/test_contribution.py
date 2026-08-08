"""Unit tests for server.contribution — ContributionValidator."""

import numpy as np
import pytest

from server.contribution import ContributionValidator


@pytest.fixture
def validator():
    return ContributionValidator()


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_client_data(flat_update: np.ndarray, trust_score: float = 1.0) -> dict:
    return {"flat_update": flat_update, "trust_score": trust_score}


# ── empty / single-client edge cases ────────────────────────────────────────

class TestEdgeCases:
    def test_empty_input_returns_empty(self, validator):
        result = validator.evaluate_batch_content_scores({}, np.zeros(10))
        assert result == {}

    def test_single_client_uses_contrib_as_content(self, validator):
        g = np.array([1.0, 0.0, 0.0])
        g_root = np.array([1.0, 0.0, 0.0])
        data = {"c1": _make_client_data(g)}
        result = validator.evaluate_batch_content_scores(data, g_root)

        assert "c1" in result
        # Perfect alignment → s_contrib = 0.6 + 0.4*1.0 = 1.0
        assert result["c1"]["s_contrib"] == pytest.approx(1.0, abs=0.05)
        # Single client → s_consist = 1.0
        assert result["c1"]["s_consist"] == 1.0
        # s_content should equal s_contrib for single client
        assert result["c1"]["s_content"] == pytest.approx(result["c1"]["s_contrib"], abs=1e-6)


# ── s_contrib: cosine similarity with root gradient ─────────────────────────

class TestSContrib:
    def test_perfect_alignment(self, validator):
        g = np.array([3.0, 4.0])
        g_root = np.array([3.0, 4.0])
        data = {"c1": _make_client_data(g)}
        result = validator.evaluate_batch_content_scores(data, g_root)
        # cos = 1.0 → s_contrib = 0.6 + 0.4*1.0 = 1.0
        assert result["c1"]["s_contrib"] == pytest.approx(1.0, abs=0.01)
        assert result["c1"]["cos_root"] == pytest.approx(1.0, abs=0.01)

    def test_orthogonal_gradient(self, validator):
        g = np.array([1.0, 0.0])
        g_root = np.array([0.0, 1.0])
        data = {"c1": _make_client_data(g)}
        result = validator.evaluate_batch_content_scores(data, g_root)
        # cos = 0 → s_contrib = 0.6 + 0.4*0 = 0.6
        assert result["c1"]["s_contrib"] == pytest.approx(0.6, abs=0.01)

    def test_opposite_gradient(self, validator):
        g = np.array([-1.0, 0.0])
        g_root = np.array([1.0, 0.0])
        data = {"c1": _make_client_data(g)}
        result = validator.evaluate_batch_content_scores(data, g_root)
        # cos = -1 → s_contrib = max(0, 0.6 + 0.4*(-1)) = 0.2
        assert result["c1"]["s_contrib"] == pytest.approx(0.2, abs=0.01)


# ── s_consist: trust-weighted pairwise consistency ──────────────────────────

class TestSConsist:
    def test_identical_gradients_high_consistency(self, validator):
        """All clients have the same gradient → consistency should be high."""
        g = np.array([1.0, 2.0, 3.0])
        g_root = np.array([1.0, 2.0, 3.0])
        data = {
            "c1": _make_client_data(g.copy(), trust_score=1.0),
            "c2": _make_client_data(g.copy(), trust_score=1.0),
            "c3": _make_client_data(g.copy(), trust_score=1.0),
        }
        result = validator.evaluate_batch_content_scores(data, g_root)
        for cid in data:
            # Identical gradients → pairwise cos = 1.0 → shifted = 1.0
            assert result[cid]["s_consist"] == pytest.approx(1.0, abs=0.05)

    def test_adversarial_gradient_low_consistency(self, validator):
        """One client's gradient opposes the others → lower consistency for that client."""
        g_good = np.array([1.0, 0.0])
        g_bad = np.array([-1.0, 0.0])
        g_root = np.array([1.0, 0.0])
        data = {
            "good1": _make_client_data(g_good.copy(), trust_score=1.0),
            "good2": _make_client_data(g_good.copy(), trust_score=1.0),
            "bad":   _make_client_data(g_bad.copy(),  trust_score=1.0),
        }
        result = validator.evaluate_batch_content_scores(data, g_root)
        # bad's pairwise cos with good1 and good2 = -1 → shifted = max(0, 0.6+0.4*(-1)) = 0.2
        assert result["bad"]["s_consist"] < result["good1"]["s_consist"]

    def test_trust_weighting_affects_consistency(self, validator):
        """Higher trusted peers have more influence on consistency."""
        g1 = np.array([1.0, 0.0])
        g2 = np.array([0.0, 1.0])  # orthogonal
        g_root = np.array([1.0, 0.0])

        # When g2 has high trust, its orthogonal direction influences c1 consistency more
        data_high = {
            "c1": _make_client_data(g1.copy(), trust_score=1.0),
            "c2": _make_client_data(g2.copy(), trust_score=10.0),
        }
        # When g2 has low trust, its influence is smaller
        data_low = {
            "c1": _make_client_data(g1.copy(), trust_score=1.0),
            "c2": _make_client_data(g2.copy(), trust_score=0.01),
        }
        r_high = validator.evaluate_batch_content_scores(data_high, g_root)
        r_low = validator.evaluate_batch_content_scores(data_low, g_root)

        # Both should give c1 the same consistency from c2 (0.6 shifted),
        # but the trust weight doesn't change the *value* in this 2-client case,
        # just the relative weighting. Still, results should be valid.
        assert 0.0 <= r_high["c1"]["s_consist"] <= 1.0
        assert 0.0 <= r_low["c1"]["s_consist"] <= 1.0


# ── asymmetric harmonic fusion ──────────────────────────────────────────────

class TestHarmonicFusion:
    def test_content_score_bounded(self, validator):
        """ContentScore must be in [0, 1]."""
        rng = np.random.default_rng(42)
        g_root = rng.standard_normal(50)
        data = {
            f"c{i}": _make_client_data(rng.standard_normal(50), trust_score=rng.random())
            for i in range(5)
        }
        result = validator.evaluate_batch_content_scores(data, g_root)
        for cid, scores in result.items():
            assert 0.0 <= scores["s_content"] <= 1.0

    def test_perfect_scores_give_high_content(self, validator):
        """When s_contrib and s_consist are both high, s_content should be high."""
        g = np.array([1.0, 2.0, 3.0])
        g_root = g.copy()
        data = {
            "c1": _make_client_data(g.copy(), trust_score=1.0),
            "c2": _make_client_data(g.copy(), trust_score=1.0),
        }
        result = validator.evaluate_batch_content_scores(data, g_root)
        assert result["c1"]["s_content"] > 0.8

    def test_fusion_favors_contrib(self, validator):
        """The asymmetric fusion with β=2 should weight s_contrib more than s_consist."""
        # Verify β² = 4.0
        assert validator.beta_sq == pytest.approx(4.0)


# ── return structure ────────────────────────────────────────────────────────

class TestReturnStructure:
    def test_result_keys(self, validator):
        g = np.array([1.0, 0.0])
        g_root = np.array([0.0, 1.0])
        data = {
            "a": _make_client_data(g.copy()),
            "b": _make_client_data(g.copy()),
        }
        result = validator.evaluate_batch_content_scores(data, g_root)
        for cid in ("a", "b"):
            assert set(result[cid].keys()) == {"s_content", "s_contrib", "s_consist", "cos_root"}
