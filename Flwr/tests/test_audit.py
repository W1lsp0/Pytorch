"""Unit tests for server.audit — AuditLogger."""

import json
import os
import tempfile

import pytest

from server.audit import AuditLogger


@pytest.fixture
def tmp_log_dir(tmp_path):
    return str(tmp_path / "test_logs")


@pytest.fixture
def logger(tmp_log_dir):
    return AuditLogger(log_dir=tmp_log_dir)


# ── directory creation ──────────────────────────────────────────────────────

class TestInit:
    def test_creates_log_directory(self, tmp_log_dir):
        assert not os.path.exists(tmp_log_dir)
        AuditLogger(log_dir=tmp_log_dir)
        assert os.path.isdir(tmp_log_dir)

    def test_main_log_path(self, logger, tmp_log_dir):
        assert logger.main_log_path == os.path.join(tmp_log_dir, "tmaa_server_audit.log")


# ── log() ───────────────────────────────────────────────────────────────────

class TestLog:
    def test_writes_single_message(self, logger):
        logger.log("hello world")
        with open(logger.main_log_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "hello world" in content

    def test_appends_messages(self, logger):
        logger.log("first")
        logger.log("second")
        with open(logger.main_log_path, "r", encoding="utf-8") as f:
            lines = f.read().strip().split("\n")
        assert len(lines) == 2
        assert "first" in lines[0]
        assert "second" in lines[1]

    def test_unicode_support(self, logger):
        logger.log("测试中文日志 ✅")
        with open(logger.main_log_path, "r", encoding="utf-8") as f:
            assert "测试中文日志" in f.read()


# ── log_batch() ─────────────────────────────────────────────────────────────

class TestLogBatch:
    def test_empty_batch_no_file(self, logger):
        logger.log_batch([])
        assert not os.path.exists(logger.main_log_path)

    def test_batch_writes_all_messages(self, logger):
        msgs = ["line1", "line2", "line3"]
        logger.log_batch(msgs)
        with open(logger.main_log_path, "r", encoding="utf-8") as f:
            content = f.read()
        for m in msgs:
            assert m in content


# ── log_client_event() ──────────────────────────────────────────────────────

class TestLogClientEvent:
    def test_logs_worker_0000_event(self, logger, tmp_log_dir):
        report = {"anomaly_score": 0.5, "status": "suspicious"}
        logger.log_client_event(
            client_cid="0",
            tee_id="worker_0000_abc",
            server_round=3,
            report=report,
        )
        path = os.path.join(tmp_log_dir, "client_0_audit.json")
        assert os.path.exists(path)
        with open(path, "r", encoding="utf-8") as f:
            entry = json.loads(f.readline())
        assert entry["round"] == 3
        assert entry["report"]["anomaly_score"] == 0.5
        assert "timestamp" in entry

    def test_logs_client_cid_zero(self, logger, tmp_log_dir):
        """Client with cid='0' should also be logged."""
        logger.log_client_event(
            client_cid="0",
            tee_id="other_tee",
            server_round=1,
            report={"ok": True},
        )
        path = os.path.join(tmp_log_dir, "client_0_audit.json")
        assert os.path.exists(path)

    def test_non_worker_0000_not_logged(self, logger, tmp_log_dir):
        """Other clients should NOT be logged to client_0_audit.json."""
        logger.log_client_event(
            client_cid="5",
            tee_id="worker_0005_xyz",
            server_round=2,
            report={"ok": True},
        )
        path = os.path.join(tmp_log_dir, "client_0_audit.json")
        assert not os.path.exists(path)

    def test_multiple_events_appended(self, logger, tmp_log_dir):
        for r in range(3):
            logger.log_client_event("0", "worker_0000", r, {"round": r})
        path = os.path.join(tmp_log_dir, "client_0_audit.json")
        with open(path, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]
        assert len(lines) == 3
        assert [l["round"] for l in lines] == [0, 1, 2]
