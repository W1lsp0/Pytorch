"""Unit tests for Client.tmaa.tee_sim — SimulatedTEE."""

import pytest

from Client.tmaa.tee_sim import SimulatedTEE


@pytest.fixture
def tee():
    return SimulatedTEE(device_id="test_device_001")


# ── sign_data ───────────────────────────────────────────────────────────────

class TestSignData:
    def test_signature_is_hex_string(self, tee):
        sig = tee.sign_data({"key": "value"})
        assert isinstance(sig, str)
        # SHA-256 hex digest is 64 characters
        assert len(sig) == 64
        int(sig, 16)  # should parse as hex without error

    def test_deterministic_signature(self, tee):
        data = {"a": 1, "b": [2, 3]}
        sig1 = tee.sign_data(data)
        sig2 = tee.sign_data(data)
        assert sig1 == sig2

    def test_different_data_different_signature(self, tee):
        sig1 = tee.sign_data({"x": 1})
        sig2 = tee.sign_data({"x": 2})
        assert sig1 != sig2

    def test_key_order_independent(self, tee):
        """json.dumps(sort_keys=True) should make field order irrelevant."""
        sig1 = tee.sign_data({"b": 2, "a": 1})
        sig2 = tee.sign_data({"a": 1, "b": 2})
        assert sig1 == sig2

    def test_different_devices_different_signatures(self):
        tee1 = SimulatedTEE(device_id="device_A")
        tee2 = SimulatedTEE(device_id="device_B")
        data = {"msg": "hello"}
        assert tee1.sign_data(data) != tee2.sign_data(data)

    def test_empty_dict(self, tee):
        sig = tee.sign_data({})
        assert isinstance(sig, str) and len(sig) == 64


# ── get_attestation_report ──────────────────────────────────────────────────

class TestAttestationReport:
    def test_report_structure(self, tee):
        report = tee.get_attestation_report()
        assert report["device_id"] == "test_device_001"
        assert report["tee_type"] == "Simulated_v1.0"
        assert report["fw_version"] == "1.0.2"
        assert report["secure_boot"] is True
        assert "timestamp" in report

    def test_timestamp_is_iso_format(self, tee):
        from datetime import datetime

        report = tee.get_attestation_report()
        # Should not raise
        datetime.fromisoformat(report["timestamp"])

    def test_different_device_ids(self):
        tee = SimulatedTEE(device_id="custom_42")
        report = tee.get_attestation_report()
        assert report["device_id"] == "custom_42"


# ── __init__ ────────────────────────────────────────────────────────────────

class TestInit:
    def test_default_device_id(self):
        tee = SimulatedTEE()
        assert tee.device_id == "simulated_device_001"

    def test_custom_device_id(self):
        tee = SimulatedTEE(device_id="my_tee")
        assert tee.device_id == "my_tee"

    def test_private_key_includes_device_id(self):
        tee = SimulatedTEE(device_id="xyz")
        assert "xyz" in tee._private_key_secret
