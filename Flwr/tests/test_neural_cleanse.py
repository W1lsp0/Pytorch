"""Unit tests for server.neural_cleanse — MAD outlier detection logic.

The full reverse-engineering optimisation requires a real model and data
loader, so we test the statistical / detection logic in neural_cleanse_scan
by mocking reverse_engineer_trigger and directly exercising the MAD
computation.
"""

import numpy as np
import pytest
from unittest.mock import patch, MagicMock

from server.neural_cleanse import neural_cleanse_scan


def _fake_trigger_factory(norms_by_class: list):
    """Return a mock reverse_engineer_trigger that yields pre-set norms."""
    call_idx = {"i": 0}

    def _fake(*args, **kwargs):
        idx = call_idx["i"]
        call_idx["i"] += 1
        return norms_by_class[idx]

    return _fake


@pytest.fixture
def dummy_model():
    return MagicMock()


@pytest.fixture
def dummy_loader():
    return MagicMock()


@pytest.fixture
def device():
    import torch
    return torch.device("cpu")


# ── MAD outlier detection ───────────────────────────────────────────────────

class TestNeuralCleanseScan:
    @patch("server.neural_cleanse.reverse_engineer_trigger")
    def test_no_backdoor_low_anomaly(self, mock_re, dummy_model, dummy_loader, device):
        """When all norms are similar, anomaly index should be low."""
        # All classes have similar mask norms → no outlier
        norms = [10.0] * 10
        mock_re.side_effect = norms

        anomaly, suspect, mask_norms = neural_cleanse_scan(
            dummy_model, dummy_loader, device, num_classes=10
        )
        assert len(mask_norms) == 10
        # With identical norms, MAD → 0, formula gives 0/epsilon
        # anomaly index should be 0 (no class stands out)
        assert anomaly == pytest.approx(0.0, abs=0.1)

    @patch("server.neural_cleanse.reverse_engineer_trigger")
    def test_backdoor_class_detected(self, mock_re, dummy_model, dummy_loader, device):
        """One class with anomalously small norm should be flagged."""
        norms = [10.0] * 10
        norms[3] = 0.5  # Class 3 is backdoored
        mock_re.side_effect = norms

        anomaly, suspect, mask_norms = neural_cleanse_scan(
            dummy_model, dummy_loader, device, num_classes=10
        )
        assert suspect == 3
        assert anomaly > 2.0  # Strong outlier

    @patch("server.neural_cleanse.reverse_engineer_trigger")
    def test_returns_correct_mask_norms(self, mock_re, dummy_model, dummy_loader, device):
        norms = [float(i) + 1.0 for i in range(10)]
        mock_re.side_effect = norms

        _, _, mask_norms = neural_cleanse_scan(
            dummy_model, dummy_loader, device, num_classes=10
        )
        assert mask_norms == norms

    @patch("server.neural_cleanse.reverse_engineer_trigger")
    def test_two_classes(self, mock_re, dummy_model, dummy_loader, device):
        """With only 2 classes, detection still works."""
        norms = [10.0, 1.0]
        mock_re.side_effect = norms

        anomaly, suspect, mask_norms = neural_cleanse_scan(
            dummy_model, dummy_loader, device, num_classes=2
        )
        assert suspect == 1  # smaller norm
        assert len(mask_norms) == 2

    @patch("server.neural_cleanse.reverse_engineer_trigger")
    def test_single_class(self, mock_re, dummy_model, dummy_loader, device):
        """Edge case: single class."""
        norms = [5.0]
        mock_re.side_effect = norms

        anomaly, suspect, mask_norms = neural_cleanse_scan(
            dummy_model, dummy_loader, device, num_classes=1
        )
        assert len(mask_norms) == 1
        # With one class, MAD → 0, anomaly = (median - norm) / epsilon
        # 0 / epsilon → 0
        assert anomaly == pytest.approx(0.0, abs=0.1)


# ── MAD math sanity ─────────────────────────────────────────────────────────

class TestMADMath:
    def test_mad_formula_manually(self):
        """Verify the MAD formula against known values."""
        norms = np.array([10.0, 10.0, 10.0, 10.0, 1.0])
        median = np.median(norms)  # 10.0
        mad = np.median(np.abs(norms - median))  # median of [0,0,0,0,9] = 0

        # When MAD is tiny, code uses 1e-6 floor
        mad = max(mad, 1e-6)
        anomaly_indices = (median - norms) / (1.4826 * mad)

        # Class 4 (norm=1.0) should have the highest anomaly index
        assert np.argmax(anomaly_indices) == 4
        assert float(np.max(anomaly_indices)) > 0
