"""Tests for smoke-test log health checks."""

from __future__ import annotations

from mcserver import config
from mcserver.tools import stub_state
from mcserver.tools.process import manager as process


def test_smoke_test_fails_on_real_log_error(isolated_server, monkeypatch) -> None:
    monkeypatch.setattr(config, "MC_PROCESS_MODE", "real")
    monkeypatch.setattr(process, "check_process_alive", lambda: {"ok": True, "alive": True, "pid": 123})
    config.SERVER_LOG.write_text(
        "[INFO] Starting server\n"
        "[ERROR] Could not load plugin WorldEdit: zip END header not found\n",
        encoding="utf-8",
    )

    result = stub_state.run_smoke_test()

    assert result["passed"] is False
    assert result["process_alive"] is True
    assert result["error_seen"] is True
    assert "ERROR" in result["matched_patterns"]


def test_smoke_test_passes_on_clean_real_log(isolated_server, monkeypatch) -> None:
    monkeypatch.setattr(config, "MC_PROCESS_MODE", "real")
    monkeypatch.setattr(process, "check_process_alive", lambda: {"ok": True, "alive": True, "pid": 123})
    config.SERVER_LOG.write_text(
        "[INFO] Starting server\n"
        '[INFO] Done (1.234s)! For help, type "help"\n',
        encoding="utf-8",
    )

    result = stub_state.run_smoke_test()

    assert result["passed"] is True
    assert result["error_seen"] is False
    assert result["matched_patterns"] == []

