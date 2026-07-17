"""Tests for process manager helpers (no real Java start)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from mcserver.tools.process import manager as process


def test_use_real_process_respects_stub_mode(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("mcserver.config.MC_PROCESS_MODE", "stub")
    monkeypatch.setattr("mcserver.config.SERVER_DIR", tmp_path)
    assert process.use_real_process() is False


def test_use_real_process_auto_when_jar_exists(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("mcserver.config.MC_PROCESS_MODE", "auto")
    monkeypatch.setattr("mcserver.config.SERVER_DIR", tmp_path)
    monkeypatch.setattr("mcserver.config.MC_SERVER_JAR", "server.jar")
    (tmp_path / "server.jar").write_bytes(b"fake")
    assert process.use_real_process() is True
    assert process.jar_available() is True


def test_check_process_alive_clears_stale_pid(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("mcserver.config.SERVER_DIR", tmp_path)
    pid_file = tmp_path / "mcserver.pid"
    pid_file.write_text("99999999\n", encoding="utf-8")
    with patch.object(process, "is_alive", return_value=False):
        result = process.check_process_alive()
    assert result["alive"] is False
    assert result["pid"] is None
    assert not pid_file.exists()


def test_start_fails_without_jar(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("mcserver.config.SERVER_DIR", tmp_path)
    monkeypatch.setattr("mcserver.config.MC_SERVER_JAR", "server.jar")
    result = process.start_server()
    assert result["ok"] is False
    assert "not found" in result["error"].lower()


def test_stop_uses_rcon_before_force_kill(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("mcserver.config.SERVER_DIR", tmp_path)
    monkeypatch.setattr("mcserver.config.MC_RCON_ENABLED", True)
    monkeypatch.setattr("mcserver.config.MC_RCON_PASSWORD", "secret")
    (tmp_path / "mcserver.pid").write_text("123\n", encoding="utf-8")

    with (
        patch.object(process, "is_alive", side_effect=[True, False, False]),
        patch.object(
            process,
            "_try_rcon_stop",
            return_value={
                "attempted": True,
                "ok": True,
                "error": None,
                "response": "Stopping the server",
            },
        ) as rcon_stop,
        patch.object(process, "_force_kill") as force_kill,
    ):
        result = process.stop_server()

    assert result["ok"] is True
    assert result["graceful"] is True
    assert result["graceful_method"] == "rcon"
    rcon_stop.assert_called_once_with(pid=123)
    force_kill.assert_not_called()


def test_stop_uses_rcon_without_pid_for_external_server(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr("mcserver.config.SERVER_DIR", tmp_path)
    monkeypatch.setattr("mcserver.config.MC_RCON_ENABLED", True)
    monkeypatch.setattr("mcserver.config.MC_RCON_PASSWORD", "secret")

    with patch.object(
        process,
        "_try_rcon_stop",
        return_value={
            "attempted": True,
            "ok": True,
            "error": None,
            "response": "Stopping the server",
        },
    ) as rcon_stop:
        result = process.stop_server()

    assert result["ok"] is True
    assert result["already_stopped"] is False
    assert result["graceful"] is True
    assert result["graceful_method"] == "rcon"
    rcon_stop.assert_called_once_with(pid=None)


def test_stop_without_pid_treats_rcon_connection_failure_as_stopped(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr("mcserver.config.SERVER_DIR", tmp_path)
    monkeypatch.setattr("mcserver.config.MC_RCON_ENABLED", True)
    monkeypatch.setattr("mcserver.config.MC_RCON_PASSWORD", "secret")

    with patch.object(
        process,
        "_try_rcon_stop",
        return_value={
            "attempted": True,
            "ok": False,
            "kind": "connection",
            "error": "RCON connection failed: refused",
        },
    ):
        result = process.stop_server()

    assert result["ok"] is True
    assert result["already_stopped"] is True
    assert result["graceful"] is False
