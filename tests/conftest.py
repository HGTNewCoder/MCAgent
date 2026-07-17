"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from mcserver import config
from mcserver.tools import stub_state
from mcserver.tools.process import manager as process

BAD_JAR_NAME = "BadRollbackTest"


def _bad_jar_path():
    return config.PLUGINS_DIR / f"{BAD_JAR_NAME}.jar"


def _cleanup_bad_jar() -> None:
    bad = _bad_jar_path()
    if bad.exists():
        bad.unlink()


@pytest.fixture
def isolated_server(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Point stub tools at a temp directory for the duration of the test."""
    server_dir = tmp_path / "mock_server"
    monkeypatch.setattr(config, "SERVER_DIR", server_dir)
    monkeypatch.setattr(config, "PLUGINS_DIR", server_dir / "plugins")
    monkeypatch.setattr(config, "BACKUPS_DIR", server_dir / "backups")
    monkeypatch.setattr(config, "SERVER_LOG", server_dir / "logs" / "latest.log")
    monkeypatch.setattr(config, "MC_PROCESS_MODE", "stub")
    monkeypatch.setattr(config, "PLUGIN_BLOCKLIST", frozenset())
    monkeypatch.setattr(config, "PLUGIN_CACHE_DIR", server_dir / "plugin-cache")
    stub_state.ensure_mock_layout()
    return server_dir


def _configure_server_paths(monkeypatch: pytest.MonkeyPatch, server_dir) -> None:
    monkeypatch.setattr(config, "SERVER_DIR", server_dir)
    monkeypatch.setattr(config, "PLUGINS_DIR", server_dir / "plugins")
    monkeypatch.setattr(config, "BACKUPS_DIR", server_dir / "backups")
    monkeypatch.setattr(config, "SERVER_LOG", server_dir / "logs" / "latest.log")


@pytest.fixture
def real_server(monkeypatch: pytest.MonkeyPatch):
    """Use the local Paper install at ./server (skipped when jar is missing)."""
    server_dir = config.PROJECT_ROOT / "server"
    jar_path = server_dir / config.MC_SERVER_JAR
    if not jar_path.is_file():
        pytest.skip(f"No Paper server jar at {jar_path}")

    java = process.resolve_java_bin()
    if java is None:
        pytest.skip(
            "Java not found. Set MC_JAVA_BIN in .env "
            '(e.g. C:\\Program Files\\Java\\jdk-25.0.3\\bin\\java.exe)'
        )

    _configure_server_paths(monkeypatch, server_dir)
    monkeypatch.setattr(config, "MC_PROCESS_MODE", "real")
    monkeypatch.setattr(config, "MC_JAVA_BIN", java)
    stub_state.ensure_mock_layout()
    _cleanup_bad_jar()
    process.stop_server()

    yield server_dir

    process.stop_server()
    _cleanup_bad_jar()
