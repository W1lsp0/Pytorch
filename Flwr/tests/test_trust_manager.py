"""Unit tests for server.trust_manager — TrustScoreManager.

The real TrustScoreManager connects to MySQL on init. We mock out
all database calls so tests run without any external dependencies.
"""

import math
from unittest.mock import patch, MagicMock

import pytest

# Patch mysql.connector.connect globally so TrustScoreManager.__init__
# never touches a real database.
_MOCK_CONNECT = "mysql.connector.connect"


def _make_manager(**kwargs):
    """Create a TrustScoreManager with MySQL fully mocked."""
    from server.trust_manager import TrustScoreManager

    with patch(_MOCK_CONNECT) as mock_conn:
        # _load_state → _init_db → connect: mock cursor returns empty results
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_cursor.fetchone.return_value = (1,)  # has_risk_ema check
        mock_conn.return_value.__enter__ = lambda s: s
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value.cursor.return_value = mock_cursor

        mgr = TrustScoreManager(**kwargs)
    return mgr


# ── _clip01 ─────────────────────────────────────────────────────────────────

class TestClip01:
    def test_normal_value(self):
        from server.trust_manager import TrustScoreManager
        assert TrustScoreManager._clip01(0.5) == 0.5

    def test_below_zero(self):
        from server.trust_manager import TrustScoreManager
        assert TrustScoreManager._clip01(-0.3) == 0.0

    def test_above_one(self):
        from server.trust_manager import TrustScoreManager
        assert TrustScoreManager._clip01(1.7) == 1.0

    def test_boundary_zero(self):
        from server.trust_manager import TrustScoreManager
        assert TrustScoreManager._clip01(0.0) == 0.0

    def test_boundary_one(self):
        from server.trust_manager import TrustScoreManager
        assert TrustScoreManager._clip01(1.0) == 1.0


# ── _safe_float ─────────────────────────────────────────────────────────────

class TestSafeFloat:
    def test_normal_string(self):
        from server.trust_manager import TrustScoreManager
        assert TrustScoreManager._safe_float("3.14") == pytest.approx(3.14)

    def test_none_returns_default(self):
        from server.trust_manager import TrustScoreManager
        assert TrustScoreManager._safe_float(None) == 0.0

    def test_invalid_string_returns_default(self):
        from server.trust_manager import TrustScoreManager
        assert TrustScoreManager._safe_float("abc", default=0.5) == 0.5

    def test_int_input(self):
        from server.trust_manager import TrustScoreManager
        assert TrustScoreManager._safe_float(42) == 42.0


# ── __init__ / hyperparameters ──────────────────────────────────────────────

class TestInit:
    def test_default_hyperparameters(self):
        mgr = _make_manager()
        assert mgr.alpha == 3.0
        assert mgr.beta == 1.0
        assert mgr.gamma == 0.5

    def test_custom_hyperparameters(self):
        mgr = _make_manager(alpha=2.0, beta=0.5, gamma=1.0)
        assert mgr.alpha == 2.0
        assert mgr.beta == 0.5
        assert mgr.gamma == 1.0

    def test_empty_history_and_blacklist(self):
        mgr = _make_manager()
        # After mock init, history may be empty or populated from mock
        assert isinstance(mgr.history, dict)
        assert isinstance(mgr.blacklist, set)


# ── _ensure_history_entry ───────────────────────────────────────────────────

class TestEnsureHistoryEntry:
    def test_creates_new_entry(self):
        mgr = _make_manager()
        entry = mgr._ensure_history_entry("new_client")
        assert entry["ema_score"] == 0.5
        assert entry["rounds"] == 0
        assert entry["risk_ema"] == 0.25
        assert "new_client" in mgr.history

    def test_existing_entry_unchanged(self):
        mgr = _make_manager()
        mgr.history["c1"] = {
            "ema_score": 0.9, "rounds": 10, "risk_ema": 0.1,
            "soft_streak": 2, "soft_isolated": False,
            "risk_soft_streak": 0, "risk_hard_streak": 0,
            "risk_isolated": False, "probe_alert_streak": 0,
            "pixel_alert_streak": 0, "trigger_alert_streak": 0,
            "peer_alert_streak": 0, "peer_risk_ema": 0.0,
            "last_peer_risk": 0.0, "c1_trigger_combo_streak": 0,
            "c2_drift_combo_streak": 0, "c2_probe_streak": 0,
            "c2_peer_streak": 0, "c2_grad_streak": 0,
            "c2_memory_score": 0, "c2_quarantine_streak": 0,
            "c2_seeded": False, "any_soft_streak": 0,
        }
        entry = mgr._ensure_history_entry("c1")
        assert entry["ema_score"] == 0.9
        assert entry["rounds"] == 10

    def test_backfills_missing_keys(self):
        mgr = _make_manager()
        # Simulate old-format entry without newer keys
        mgr.history["old"] = {"ema_score": 0.7, "rounds": 5}
        entry = mgr._ensure_history_entry("old")
        assert entry["risk_ema"] == 0.25  # default
        assert entry["c2_seeded"] is False


# ── evaluate_device_integrity ───────────────────────────────────────────────

class TestEvaluateDeviceIntegrity:
    def test_tampered_file_returns_zero(self):
        mgr = _make_manager()
        report = {"metrics": {"system_integrity": {"file_tampered": True}}}
        m_attest, trust = mgr.evaluate_device_integrity("c1", report)
        assert m_attest == 0.0
        assert trust == 0.0

    def test_clean_report_high_trust(self):
        mgr = _make_manager()
        report = {
            "metrics": {
                "system_integrity": {"file_tampered": False},
                "behavior_fingerprint": {
                    "gpu_volatility": 5.0,
                    "cpu_volatility": 3.0,
                    "throughput_check": "NORMAL",
                },
            }
        }
        m_attest, trust = mgr.evaluate_device_integrity("c1", report)
        assert m_attest == 1.0
        assert trust == pytest.approx(1.0, abs=0.01)

    def test_low_volatility_reduces_trust(self):
        mgr = _make_manager()
        report = {
            "metrics": {
                "system_integrity": {"file_tampered": False},
                "behavior_fingerprint": {
                    "gpu_volatility": 0.5,
                    "cpu_volatility": 0.5,
                    "throughput_check": "NORMAL",
                },
            }
        }
        _, trust = mgr.evaluate_device_integrity("c1", report)
        # a_k = 0.4, excess = max(0, 0.4 - 0.1) = 0.3
        # penalty = exp(-5 * 0.3^2) = exp(-0.45) ≈ 0.638
        assert trust < 1.0
        assert trust == pytest.approx(math.exp(-5.0 * 0.3**2), abs=0.01)

    def test_suspected_fake_training(self):
        mgr = _make_manager()
        report = {
            "metrics": {
                "system_integrity": {"file_tampered": False},
                "behavior_fingerprint": {
                    "gpu_volatility": 5.0,
                    "cpu_volatility": 5.0,
                    "throughput_check": "SUSPECTED_FAKE_TRAINING (Too Fast)",
                },
            }
        }
        _, trust = mgr.evaluate_device_integrity("c1", report)
        # a_k = 0.6, excess = 0.5
        # penalty = exp(-5 * 0.25) = exp(-1.25) ≈ 0.287
        assert trust < 0.5

    def test_empty_metrics_defaults(self):
        mgr = _make_manager()
        report = {"metrics": {}}
        m_attest, trust = mgr.evaluate_device_integrity("c1", report)
        # No file_tampered → m_attest = 1.0
        # No fingerprint → a_k stays low
        assert m_attest == 1.0


# ── apply_proxy_loss_penalty ────────────────────────────────────────────────

class TestProxyLossPenalty:
    def test_safe_loss_no_penalty(self):
        mgr = _make_manager()
        m, t = mgr.apply_proxy_loss_penalty("c1", clean_loss=1.0, m_attest=1.0, trust_score=0.9)
        assert m == 1.0
        # loss_penalty = min(1.0, 1.5/1.0) = 1.0
        assert t == pytest.approx(0.9, abs=0.01)

    def test_high_loss_blacklists(self):
        mgr = _make_manager()
        m, t = mgr.apply_proxy_loss_penalty("c1", clean_loss=5.0, m_attest=1.0, trust_score=0.9)
        assert m == 0.0
        assert t == 0.0
        assert "c1" in mgr.blacklist

    def test_moderate_loss_reduces_trust(self):
        mgr = _make_manager()
        m, t = mgr.apply_proxy_loss_penalty("c1", clean_loss=2.0, m_attest=1.0, trust_score=1.0)
        # loss_penalty = min(1.0, 1.5/2.0) = 0.75
        assert t == pytest.approx(0.75, abs=0.01)


# ── fetch_history ───────────────────────────────────────────────────────────

class TestFetchHistory:
    def test_new_client_gets_default(self):
        mgr = _make_manager()
        score = mgr.fetch_history("brand_new")
        assert score == 0.5

    def test_blacklisted_client_gets_zero(self):
        mgr = _make_manager()
        mgr.blacklist.add("bad_client")
        assert mgr.fetch_history("bad_client") == 0.0

    def test_existing_client_returns_ema(self):
        mgr = _make_manager()
        mgr._ensure_history_entry("c1")
        mgr.history["c1"]["ema_score"] = 0.85
        assert mgr.fetch_history("c1") == 0.85


# ── fetch_risk_ema / is_risk_isolated / is_soft_isolated ────────────────────

class TestRiskQueries:
    def test_fetch_risk_ema_default(self):
        mgr = _make_manager()
        assert mgr.fetch_risk_ema("new") == 0.25

    def test_fetch_risk_ema_blacklisted(self):
        mgr = _make_manager()
        mgr.blacklist.add("bad")
        assert mgr.fetch_risk_ema("bad") == 1.0

    def test_is_risk_isolated_default(self):
        mgr = _make_manager()
        assert mgr.is_risk_isolated("new") is False

    def test_is_soft_isolated_default(self):
        mgr = _make_manager()
        assert mgr.is_soft_isolated("new") is False

    def test_is_soft_isolated_blacklisted_returns_false(self):
        mgr = _make_manager()
        mgr.blacklist.add("bad")
        assert mgr.is_soft_isolated("bad") is False


# ── _mark_blacklist ─────────────────────────────────────────────────────────

class TestMarkBlacklist:
    def test_adds_to_blacklist(self):
        mgr = _make_manager()
        mgr._ensure_history_entry("c1")
        mgr._mark_blacklist("c1", "test reason")
        assert "c1" in mgr.blacklist
        assert mgr.blacklist_reason["c1"] == "test reason"

    def test_resets_isolation_flags(self):
        mgr = _make_manager()
        mgr._ensure_history_entry("c1")
        mgr.history["c1"]["soft_isolated"] = True
        mgr.history["c1"]["risk_isolated"] = True
        mgr._mark_blacklist("c1", "reason")
        assert mgr.history["c1"]["soft_isolated"] is False
        assert mgr.history["c1"]["risk_isolated"] is False


# ── get_blacklist_reason ────────────────────────────────────────────────────

class TestGetBlacklistReason:
    def test_known_reason(self):
        mgr = _make_manager()
        mgr.blacklist_reason["c1"] = "proxy_failure"
        assert mgr.get_blacklist_reason("c1") == "proxy_failure"

    def test_unknown_returns_default(self):
        mgr = _make_manager()
        assert mgr.get_blacklist_reason("nobody") == "unknown"
