#!/usr/bin/env python3
"""State-machine regression test: quarantine must be releasable after clean evidence."""
from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server.trust_manager import TrustScoreManager


def test_recovery_with_clean_evidence() -> None:
    # MySQL is optional in the local test environment; the manager falls back
    # to its in-memory state store.
    with contextlib.redirect_stdout(io.StringIO()):
        manager = TrustScoreManager()
        entry = manager._ensure_history_entry("recovery-client")
        entry.update(
            {
                "risk_ema": 1.0,
                "risk_soft_streak": 8,
                "risk_isolated": True,
                "c2_seeded": True,
                "c2_memory_score": 10,
                "c2_quarantine_streak": 3,
                "trigger_alert_streak": 0,
                "probe_alert_streak": 0,
                "peer_alert_streak": 0,
                "pixel_alert_streak": 0,
                "c2_drift_combo_streak": 0,
                "c2_probe_streak": 0,
                "c2_peer_streak": 0,
                "c2_grad_streak": 0,
            }
        )
        zeros = {"recovery-client": 0.0}
        for _ in range(12):
            manager.update_risk_history(
                zeros,
                cos_root_scores=zeros,
                content_scores={"recovery-client": 0.5},
                entropies=zeros,
                probe_losses=zeros,
                spectral_scores=zeros,
                pixel_means=zeros,
                pixel_stds=zeros,
                trigger_br_scores=zeros,
                trigger_tl_scores=zeros,
                sign_scores=zeros,
                heavy_probe_flags={"recovery-client": False},
            )
        assert not manager.is_risk_isolated("recovery-client")
        assert manager.history["recovery-client"]["c2_memory_score"] == 0


if __name__ == "__main__":
    test_recovery_with_clean_evidence()
    print("recovery state test passed")
